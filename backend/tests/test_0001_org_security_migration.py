from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

alembic_command = pytest.importorskip("alembic.command")
alembic_config = pytest.importorskip("alembic.config")
sa = pytest.importorskip("sqlalchemy")

TEST_DATABASE_URL = os.getenv("METRO_TEST_DATABASE_URL")
BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set METRO_TEST_DATABASE_URL to a disposable PostgreSQL database.",
)
def test_org_security_migration_and_audit_log_immutability() -> None:
    cfg = alembic_config.Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    engine = sa.create_engine(TEST_DATABASE_URL)

    try:
        alembic_command.upgrade(cfg, "head")

        with engine.begin() as connection:
            roles = set(connection.execute(sa.text("SELECT name FROM security_roles")).scalars())
            assert roles == {
                "admin",
                "auditor",
                "metrologist",
                "quality_engineer",
                "viewer",
            }

            permission_count = connection.execute(
                sa.text("SELECT COUNT(*) FROM security_permissions")
            ).scalar_one()
            assert permission_count > 0

            audit_id = uuid.uuid4()
            connection.execute(
                sa.text(
                    """
                    INSERT INTO security_audit_log (
                        id,
                        action,
                        entity_type,
                        entity_id,
                        before_state,
                        after_state,
                        ip_address
                    )
                    VALUES (
                        :id,
                        'test.create',
                        'test_entity',
                        NULL,
                        NULL,
                        '{"status":"created"}'::jsonb,
                        '127.0.0.1'
                    )
                    """
                ),
                {"id": audit_id},
            )

            savepoint = connection.begin_nested()
            with pytest.raises(sa.exc.DBAPIError):
                connection.execute(
                    sa.text(
                        """
                        UPDATE security_audit_log
                        SET action = 'test.update'
                        WHERE id = :id
                        """
                    ),
                    {"id": audit_id},
                )
            savepoint.rollback()
    finally:
        engine.dispose()
        alembic_command.downgrade(cfg, "base")
