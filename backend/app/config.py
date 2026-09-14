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

        # Default storage limit (in MB) assigned to newly registered
        # students. Not enforced anywhere yet -- storage itself is a
        # later phase -- but recorded on the user from day one.
        self.default_storage_limit_mb: int = int(
            os.getenv("DEFAULT_STORAGE_LIMIT_MB", "1024")
        )

    @property
    def database_url(self) -> str:
        """Build a Postgres connection string from the individual settings."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
