# DECP Server Install Guide

How to get DECP running on the department-owned Ubuntu Server, once
it's ready to move off a personal development PC. This assumes Ubuntu
Server 24.04 LTS, per the project's stated target.

## 1. Prerequisites

```bash
sudo apt update
sudo apt install -y git

# Docker Engine + Compose plugin (official Docker install script)
curl -fsSL https://get.docker.com | sudo sh

# Let your deployment user run docker without sudo every time
sudo usermod -aG docker $USER
# log out and back in for the group change to take effect
```

Verify:

```bash
docker --version
docker compose version
```

## 2. Get the code onto the server

```bash
git clone <your-repo-url> decp
cd decp/Department-Engineering-Cloud
```

## 3. Configure `.env`

```bash
cp .env.example .env
```

Edit `.env` and set **real** values -- the placeholders in
`.env.example` are for local development only:

| Variable | What to set it to |
|---|---|
| `POSTGRES_PASSWORD` | A strong, unique password |
| `JWT_SECRET` | `python3 -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `STORAGE_HOST_PATH` | A durable path on this server, e.g. `/cloud-data` -- **not** the default `./storage-data`, which is relative to wherever you happen to run `docker compose` from |
| `CONTAINER_MEMORY_LIMIT_MB` / `CONTAINER_CPU_LIMIT` | Tuned to what this server can actually spare per student app -- see "Sizing resource limits" below |

Everything else can keep its `.env.example` default unless you have a
specific reason to change it.

## 4. Start the stack

```bash
docker compose up --build -d
docker compose exec backend alembic upgrade head
```

Verify:

```bash
docker compose ps          # all four services should be "Up" / "healthy"
curl http://localhost:8080/api/health
```

## 5. Make it reachable on the department network

The department network's firewall/router needs to forward whatever
address students will use to this server's port `8080` (or change the
`nginx` service's port mapping in `docker-compose.yml` to `80:80` and
forward port 80 instead, for a plain `http://<server-address>` URL).

DECP doesn't need any code changes for this -- every website's
`public_url` is stored as a relative path (`/sites/...`, `/apps/...`),
so it resolves correctly against whatever address students actually
use to reach the server.

## 6. Docker daemon on boot

The official Docker install already enables the `docker` systemd
service. Confirm it starts automatically after a reboot:

```bash
sudo systemctl is-enabled docker   # should print "enabled"
```

This matters for Phase 4: dynamic website containers use a
`restart_policy: unless-stopped`, so after `sudo reboot`, once the
Docker daemon comes back up, previously-`online` dynamic websites
restart automatically -- see `docs/WEBSITE-HOSTING.md`, "Server
restart behavior."

`docker-compose.yml`'s own services (`postgres`, `backend`, `frontend`,
`nginx`) all use `restart: unless-stopped` too, but Compose services
only come back automatically if something re-runs `docker compose up`
after a reboot (Docker Desktop does this on Windows; a bare Docker
Engine on Ubuntu does not, by default). Add a systemd unit or a
`@reboot` cron entry that runs `docker compose up -d` in the project
directory if you want the whole stack, not just already-running
containers, to survive a full server reboot unattended.

## 7. Sizing resource limits

The defaults (`CONTAINER_CPU_LIMIT=1.0`, `CONTAINER_MEMORY_LIMIT_MB=512`)
assume a reasonably capable shared server and a modest number of
concurrent dynamic websites. Before enabling this for a whole class:

- Estimate: `(expected concurrent dynamic websites) × 512 MB` should
  comfortably fit in the server's RAM alongside Postgres, the backend,
  and normal OS overhead.
- Lower `CONTAINER_MEMORY_LIMIT_MB` / `CONTAINER_CPU_LIMIT` if the
  server is modest, or raise `MAX_WEBSITES_PER_USER` down instead of
  raising limits, if students are hitting quota complaints but the
  server can't take more concurrent containers.
- There is currently no server-wide cap on *total* concurrent dynamic
  containers across all students -- only the per-user
  `MAX_WEBSITES_PER_USER` count and per-container resource limits.
  Watch `docker stats` under real load and adjust.

## 8. Backups

Two things need backing up; both live outside any Docker container:

- **Database**: the `postgres_data` named volume. Find its host path
  with `docker volume inspect department-engineering-cloud_postgres_data`,
  or simpler, use `pg_dump` on a schedule:
  ```bash
  docker compose exec -T postgres pg_dump -U decp_user decp > backup-$(date +%F).sql
  ```
- **Files and websites**: everything under `STORAGE_HOST_PATH`
  (personal files in `users/`, hosted websites in `websites/`) -- a
  plain filesystem backup (`rsync`, `tar`, or your usual backup tool)
  of that directory covers both.

Automated backups are a stated future phase for DECP itself; until
then, back these up the same way you'd back up any other server data.

## 9. Updating DECP on the server

```bash
cd decp/Department-Engineering-Cloud
git pull
docker compose build
docker compose up -d
docker compose exec backend alembic upgrade head   # applies any new migrations
```

Existing dynamic website containers are unaffected by this (they're
managed by `docker-py`, not `docker compose`, so rebuilding the
`backend` image doesn't touch them) -- see `docs/WEBSITE-HOSTING.md`
for why the backend reconnects to them automatically on startup either
way.

## 10. Troubleshooting

- **`docker compose exec backend ...` fails with a permission error
  talking to Docker** -- confirm the backend container can see
  `/var/run/docker.sock` (`docker compose exec backend ls -la
  /var/run/docker.sock`) and that the host's Docker daemon is running.
- **A dynamic website is stuck on `building`** -- check
  `docker compose logs backend` for the build error; a backend
  restart mid-build loses that one deployment (documented limitation,
  see WEBSITE-HOSTING.md) -- delete and redeploy it.
- **Students report their site is unreachable after a server reboot**
  -- confirm `docker compose ps` shows all four core services up
  first; if they are, the backend's own startup already reconnects it
  to every dynamic website's network (see WEBSITE-HOSTING.md) -- check
  `docker ps` for the specific student container and `docker compose
  logs backend` for errors during that reconnection step.
