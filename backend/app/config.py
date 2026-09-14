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
