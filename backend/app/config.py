"""
Application configuration.

All configuration is read from environment variables so the same
container image can run unchanged in development and on the
department Ubuntu server. No secrets are hardcoded here.
"""

import os


class Settings:
    """Simple settings object populated from environment variables."""

    def __init__(self) -> None:
        self.service_name: str = os.getenv("SERVICE_NAME", "decp-backend")
        self.environment: str = os.getenv("ENVIRONMENT", "development")

        # Database configuration
        self.postgres_db: str = os.getenv("POSTGRES_DB", "decp")
        self.postgres_user: str = os.getenv("POSTGRES_USER", "decp_user")
        self.postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")
        self.postgres_host: str = os.getenv("POSTGRES_HOST", "postgres")
        self.postgres_port: str = os.getenv("POSTGRES_PORT", "5432")

        # JWT / authentication configuration. There is no safe default
        # for the secret -- it must be provided via the environment.
        self.jwt_secret: str = os.getenv("JWT_SECRET", "")
        self.jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes: int = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        )

        # File storage configuration.
        #
        # STORAGE_ROOT is a path *inside the backend container*. Docker
        # Compose mounts a persistent host directory there (see
        # docker-compose.yml / STORAGE_HOST_PATH) so files survive
        # container restarts and `docker compose down` / `up`.
        self.storage_root: str = os.getenv("STORAGE_ROOT", "/cloud-data")

        # Default storage quota assigned to newly registered students,
        # in bytes. Stored on the user as `storage_limit` (megabytes,
        # for readability) and converted back to bytes wherever quota
        # math happens -- see app/storage/service.py.
        self.default_storage_quota_bytes: int = int(
            os.getenv("DEFAULT_STORAGE_QUOTA_BYTES", str(10 * 1024**3))  # 10 GB
        )

        # Website hosting configuration (Phase 4).
        #
        # Websites live under STORAGE_ROOT/websites/ -- a namespace
        # separate from personal files (STORAGE_ROOT/users/), so the
        # two kinds of data never mix and can be limited independently.
        self.max_website_zip_size_bytes: int = int(
            os.getenv("MAX_WEBSITE_ZIP_SIZE_BYTES", str(200 * 1024**2))  # 200 MB
        )
        self.max_website_extracted_size_bytes: int = int(
            os.getenv("MAX_WEBSITE_EXTRACTED_SIZE_BYTES", str(500 * 1024**2))  # 500 MB
        )
        self.max_website_files: int = int(os.getenv("MAX_WEBSITE_FILES", "5000"))
        self.max_websites_per_user: int = int(os.getenv("MAX_WEBSITES_PER_USER", "5"))

        # Resource limits applied to every dynamic website's container.
        # Kept modest by default -- this runs on one shared department
        # machine, not a dedicated cluster.
        self.container_cpu_limit: float = float(os.getenv("CONTAINER_CPU_LIMIT", "1.0"))
        self.container_memory_limit_mb: int = int(os.getenv("CONTAINER_MEMORY_LIMIT_MB", "512"))
        self.container_pids_limit: int = int(os.getenv("CONTAINER_PIDS_LIMIT", "100"))
        self.docker_build_timeout_seconds: int = int(
            os.getenv("DOCKER_BUILD_TIMEOUT_SECONDS", "300")
        )

        # The backend's own container name, set via `container_name` in
        # docker-compose.yml. Needed so the backend can connect itself
        # to each dynamic website's dedicated Docker network in order
        # to reverse-proxy to it -- see app/deploy/containers.py.
        self.backend_container_name: str = os.getenv("BACKEND_CONTAINER_NAME", "decp-backend")

        # Admin dashboard configuration (Phase 5).
        #
        # How often a system_metrics sample is taken (see
        # app/admin/metrics.py) and how long samples are kept before
        # being pruned, so the table doesn't grow forever.
        self.metrics_sample_interval_seconds: int = int(
            os.getenv("METRICS_SAMPLE_INTERVAL_SECONDS", "60")
        )
        self.metrics_retention_days: int = int(os.getenv("METRICS_RETENTION_DAYS", "14"))

        # Storage usage thresholds (percent of total department
        # storage) used to color the admin storage-health indicator.
        self.storage_warning_percent: float = float(
            os.getenv("STORAGE_WARNING_PERCENT", "70")
        )
        self.storage_critical_percent: float = float(
            os.getenv("STORAGE_CRITICAL_PERCENT", "85")
        )

        # Names of the DECP-managed containers whose logs an admin may
        # view (see app/admin/service.py) -- a fixed allowlist, never a
        # client-supplied name, so this can never be used to read logs
        # from an arbitrary container on the host.
        self.core_service_containers: dict[str, str] = {
            "backend": self.backend_container_name,
            "nginx": os.getenv("NGINX_CONTAINER_NAME", "department-engineering-cloud-nginx-1"),
            "postgres": os.getenv(
                "POSTGRES_CONTAINER_NAME", "department-engineering-cloud-postgres-1"
            ),
        }

    @property
    def default_storage_limit_mb(self) -> int:
        """Default per-user quota, in megabytes, derived from the bytes setting."""
        return self.default_storage_quota_bytes // (1024 * 1024)

    @property
    def database_url(self) -> str:
        """Build a Postgres connection string from the individual settings."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
