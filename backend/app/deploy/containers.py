"""
Docker container lifecycle management for dynamic website deployments.

Uses the Docker SDK (docker-py) against the host's Docker daemon,
reached via /var/run/docker.sock mounted into the *backend* container
only -- this is never mounted into a student container (see docker-
compose.yml). Student code never talks to the Docker daemon.

Isolation model (full detail in docs/WEBSITE-HOSTING.md):
  - Every dynamic website gets its own dedicated bridge network,
    created here and named after the website's id.
  - The backend container joins that network so it can reverse-proxy
    to the app by container name (see app/api/public_sites.py) --
    nothing else joins it.
  - The student's container joins ONLY that network: no route to
    Postgres, the backend's other traffic, or any other student's
    container or network.
  - The container gets no docker.sock, no host filesystem mount, no
    published host port, and none of DECP's own environment variables
    or secrets -- only PORT, matching the framework template's
    internal listen port.
  - CPU, memory, and process-count limits are applied to every
    container (see app.config.settings).
"""

import docker
from docker.errors import APIError, BuildError, NotFound

from app.config import settings

_client: docker.DockerClient | None = None


def _get_client() -> docker.DockerClient:
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def network_name(website_id: str) -> str:
    return f"decp-app-{website_id}"


def container_name(website_id: str) -> str:
    return f"decp-site-{website_id}"


def image_tag(website_id: str) -> str:
    return f"decp-site-{website_id}:latest"


def build_image(build_dir: str, tag: str) -> str:
    """Build a Docker image from a DECP-controlled build directory."""
    client = _get_client()
    try:
        image, _log_stream = client.images.build(
            path=build_dir,
            tag=tag,
            rm=True,
            forcerm=True,
            timeout=settings.docker_build_timeout_seconds,
        )
    except BuildError as exc:
        log_tail = "\n".join(
            entry.get("stream", "").rstrip("\n")
            for entry in exc.build_log
            if isinstance(entry, dict) and entry.get("stream")
        )
        raise RuntimeError(f"Docker image build failed: {exc}\n{log_tail[-4000:]}") from exc
    except APIError as exc:
        raise RuntimeError(f"Docker image build failed: {exc}") from exc
    return image.id


def run_container(website_id: str, tag: str, name: str, internal_port: int) -> str:
    """
    Create the website's dedicated network, connect the backend to it,
    and start the container on it. Returns the container id.
    """
    client = _get_client()
    net_name = network_name(website_id)

    try:
        network = client.networks.get(net_name)
    except NotFound:
        network = client.networks.create(net_name, driver="bridge")

    try:
        backend = client.containers.get(settings.backend_container_name)
        network.connect(backend)
    except APIError:
        pass  # already connected

    container = client.containers.run(
        tag,
        name=name,
        detach=True,
        network=net_name,
        restart_policy={"Name": "unless-stopped"},
        mem_limit=f"{settings.container_memory_limit_mb}m",
        nano_cpus=int(settings.container_cpu_limit * 1_000_000_000),
        pids_limit=settings.container_pids_limit,
        security_opt=["no-new-privileges"],
        cap_drop=["ALL"],
        environment={"PORT": str(internal_port)},
    )
    return container.id


def ensure_backend_connected(website_id: str) -> None:
    """
    Make sure the *current* backend container is connected to a
    website's dedicated network.

    This matters because the network↔container attachment made in
    run_container() is tracked by the Docker daemon, not by Docker
    Compose -- if the backend container is later recreated (e.g. a
    plain `docker compose up` after `down`, or `docker compose up
    --build`), the new container starts with none of those extra
    connections. Called for every dynamic website at backend startup
    (see app.deploy.service.reconnect_all_dynamic_websites) so
    reverse-proxying keeps working after a restart without requiring
    every website to be redeployed.
    """
    client = _get_client()
    net_name = network_name(website_id)
    try:
        network = client.networks.get(net_name)
        backend = client.containers.get(settings.backend_container_name)
        network.connect(backend)
    except APIError:
        pass  # already connected, or the network/container is gone
    except NotFound:
        pass


def stop_container(container_id: str) -> None:
    client = _get_client()
    try:
        client.containers.get(container_id).stop(timeout=10)
    except NotFound:
        pass


def start_container(container_id: str) -> None:
    client = _get_client()
    try:
        client.containers.get(container_id).start()
    except NotFound as exc:
        raise RuntimeError("The container no longer exists") from exc


def restart_container(container_id: str) -> None:
    client = _get_client()
    try:
        client.containers.get(container_id).restart(timeout=10)
    except NotFound as exc:
        raise RuntimeError("The container no longer exists") from exc


def get_logs(container_id: str, tail: int = 200) -> str:
    client = _get_client()
    try:
        container = client.containers.get(container_id)
    except NotFound:
        return "(container no longer exists)"
    return container.logs(tail=tail, timestamps=True).decode("utf-8", errors="replace")


def is_running(container_id: str) -> bool:
    client = _get_client()
    try:
        container = client.containers.get(container_id)
    except NotFound:
        return False
    return container.status == "running"


def remove_container_and_network(website_id: str, container_id: str | None) -> None:
    """Best-effort teardown -- used during website deletion."""
    client = _get_client()

    if container_id:
        try:
            client.containers.get(container_id).remove(force=True)
        except NotFound:
            pass

    net_name = network_name(website_id)
    try:
        network = client.networks.get(net_name)
        try:
            backend = client.containers.get(settings.backend_container_name)
            network.disconnect(backend, force=True)
        except (NotFound, APIError):
            pass
        network.remove()
    except NotFound:
        pass


def list_managed_containers() -> list[dict]:
    """
    List every container DECP created for a dynamic website (name
    prefix "decp-site-"). Used only by the admin dashboard -- never
    lists arbitrary host containers, since the filter is a fixed
    prefix DECP itself controls, not a client-supplied value.
    """
    client = _get_client()
    containers = client.containers.list(all=True, filters={"name": "decp-site-"})
    return [
        {
            "id": c.id,
            "name": c.name,
            "status": c.status,
            "image": (c.image.tags[0] if c.image.tags else c.image.short_id),
        }
        for c in containers
    ]


def _calculate_cpu_percent(stats: dict) -> float:
    try:
        cpu_delta = (
            stats["cpu_stats"]["cpu_usage"]["total_usage"]
            - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        )
        system_delta = (
            stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
        )
        online_cpus = stats["cpu_stats"].get("online_cpus") or len(
            stats["cpu_stats"]["cpu_usage"].get("percpu_usage") or [1]
        )
        if system_delta > 0 and cpu_delta > 0:
            return (cpu_delta / system_delta) * online_cpus * 100.0
    except (KeyError, TypeError, ZeroDivisionError):
        pass
    return 0.0


def container_stats(container_id: str) -> dict | None:
    """
    A single non-streaming CPU/memory snapshot for one container, or
    None if it no longer exists. Not running is a normal, healthy
    result (a stopped website) -- reported as zeroed-out usage rather
    than an error.
    """
    client = _get_client()
    try:
        container = client.containers.get(container_id)
    except NotFound:
        return None

    if container.status != "running":
        return {"status": container.status, "cpu_percent": 0.0, "memory_bytes": 0, "memory_limit_bytes": 0}

    try:
        raw = container.stats(stream=False)
    except APIError:
        return {"status": container.status, "cpu_percent": 0.0, "memory_bytes": 0, "memory_limit_bytes": 0}

    memory_stats = raw.get("memory_stats", {})
    return {
        "status": container.status,
        "cpu_percent": _calculate_cpu_percent(raw),
        "memory_bytes": memory_stats.get("usage", 0),
        "memory_limit_bytes": memory_stats.get("limit", 0),
    }


def core_service_status(name: str) -> str:
    """
    "running" / "not-found" / a Docker status string for one of
    DECP's own core containers (see settings.core_service_containers
    -- a fixed, server-side name mapping, never a client-supplied
    container name).
    """
    client = _get_client()
    try:
        return client.containers.get(name).status
    except NotFound:
        return "not-found"


def docker_available() -> bool:
    try:
        return bool(_get_client().ping())
    except Exception:
        return False


def remove_image(tag: str) -> None:
    client = _get_client()
    try:
        client.images.remove(tag, force=True)
    except (NotFound, APIError):
        pass
