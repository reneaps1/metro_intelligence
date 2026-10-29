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
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Application ---
    app_env: str
    app_secret_key: str
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str

    # --- Edition (IQ-F1, docs/tasks/IQ-plan-demo-industrial-quality.md D5) ---
    # "metrology" = measurement monitoring only (the original product);
    # "industrial" = adds the industrial-quality demo, IIoT signals and AI lab.
    # Defaults to metrology so a missing variable never exposes new modules.
    app_edition: Literal["metrology", "industrial"] = "metrology"
    # Customer-facing label shown by the industrial demo. The real customer
    # name is only ever set in the deployment environment, never in the repo.
    demo_client_label: str = "Cliente demo"
    # IQ-F5: optional path to a PRIVATE JSON with the customer's historical
    # report summary (kept outside the repo). Unset = illustrative placeholder.
    demo_report_summary_path: str | None = None
    # IQ-F7: optional path to a PRIVATE JSON with the customer's precomputed
    # ML/DL study results (kept outside the repo). Unset = illustrative placeholder.
    demo_model_lab_path: str | None = None
    # IQ-F6: exploratory dimensional CSV import (in memory only, never persisted).
    # Files larger than the byte cap are analysed as a sample of their head.
    dimensional_import_max_rows: int = Field(default=200_000, ge=1_000, le=2_000_000)
    dimensional_import_max_mb: int = Field(default=20, ge=1, le=200)
    dimensional_import_ttl_minutes: int = Field(default=240, ge=5, le=24 * 60)
    # IQ-F10 (plan decision D8): optional path to the manifest.json of the
    # customer's REAL dataset, converted offline into a PRIVATE folder. Local
    # use only: ignored when APP_ENV=production. Unset = not offered.
    demo_real_dataset_path: str | None = None
    demo_real_dataset_max_mb: int = Field(default=200, ge=1, le=2_000)
    demo_real_dataset_max_pieces: int = Field(default=1_000_000, ge=1_000, le=10_000_000)
    # IQ-F19 (plan decision D13): optional PRIVATE JSON with X/Y nominals and
    # position tolerances for the REAL dataset (`connectors/pin_spec.py`).
    # Unset or invalid = the REAL dataset has no X/Y position view.
    demo_real_spec_path: str | None = None

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
