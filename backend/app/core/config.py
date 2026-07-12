"""F4.1 (MI-21): typed settings loaded from environment variables only
(CLAUDE.md §5 — no hardcoded config/credentials). Every field mirrors a
variable documented in .env.example; a missing required variable raises a
pydantic ValidationError naming the exact field, so misconfiguration fails
loudly at startup instead of surfacing later as a confusing runtime error.

`env_file=".env"` is a local-dev convenience only (pydantic-settings only
reads it if the file exists) -- Docker Compose and CI inject real
environment variables directly, never through this file."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Application ---
    app_env: str
    app_secret_key: str
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str

    # --- Database (PostgreSQL 16) ---
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str

    # --- Auth (values loaded now; JWT issuing/verification lands in F4.2) ---
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- Object storage (MinIO) ---
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket_raw_files: str
    minio_use_tls: bool = False

    # --- Observability ---
    log_level: str = "INFO"
    enable_metrics: bool = True

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    # Fields are required-but-populated-from-env at runtime (pydantic-settings);
    # mypy can't see that, hence the standard pydantic-settings ignore here.
    return Settings()  # type: ignore[call-arg]
