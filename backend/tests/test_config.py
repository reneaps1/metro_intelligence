"""F4.1 (MI-21) acceptance criterion: config loading fails clearly if a
required env var is missing, and every setting comes from the environment
(no hardcoded values -- CLAUDE.md §5)."""
from __future__ import annotations

import pytest
from app.core.config import Settings
from pydantic import ValidationError

REQUIRED_ENV_VARS = {
    "APP_ENV": "development",
    "APP_SECRET_KEY": "test-secret",
    "CORS_ORIGINS": "http://localhost:5173",
    "POSTGRES_HOST": "db",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "metro_intelligence",
    "POSTGRES_USER": "metro_app",
    "POSTGRES_PASSWORD": "test-password",
    "JWT_SECRET": "test-jwt-secret",
    "MINIO_ENDPOINT": "minio:9000",
    "MINIO_ACCESS_KEY": "test-access-key",
    "MINIO_SECRET_KEY": "test-secret-key",
    "MINIO_BUCKET_RAW_FILES": "raw-measurement-files",
}


def _set_all_required_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in REQUIRED_ENV_VARS.items():
        monkeypatch.setenv(key, value)


def test_settings_loads_every_required_value_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_all_required_env_vars(monkeypatch)

    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.postgres_port == 5432
    assert settings.database_url == "postgresql+psycopg://metro_app:test-password@db:5432/metro_intelligence"
    assert settings.cors_origin_list == ["http://localhost:5173"]


@pytest.mark.parametrize("missing_key", sorted(REQUIRED_ENV_VARS))
def test_settings_fails_clearly_when_a_required_var_is_missing(
    monkeypatch: pytest.MonkeyPatch, missing_key: str
) -> None:
    _set_all_required_env_vars(monkeypatch)
    monkeypatch.delenv(missing_key, raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert missing_key.lower() in str(exc_info.value)
