"""purge_domain_data keeps identities and the audit trail, empties the rest."""

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
    not TEST_DATABASE_URL, reason="Set METRO_TEST_DATABASE_URL to a disposable PostgreSQL database."
)
def test_purge_keeps_users_roles_and_audit_and_empties_domain_tables() -> None:
    from app.cli.purge_domain_data import AUDIT_ACTION, purge
    from app.services.domain_purge import count_domain_rows

    cfg = alembic_config.Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    engine = sa.create_engine(TEST_DATABASE_URL)
    try:
        alembic_command.upgrade(cfg, "head")
        with engine.begin() as conn:
            user_id = uuid.uuid4()
            conn.execute(
                sa.text(
                    "INSERT INTO security_users (id, email, display_name, password_hash, is_active) "
                    "VALUES (:id, 'purge.test@demo.local', 'Purge Test', 'x', true)"
                ),
                {"id": user_id},
            )
            conn.execute(
                sa.text(
                    "INSERT INTO security_user_roles (user_id, role_id) "
                    "SELECT :user_id, id FROM security_roles WHERE name = 'admin'"
                ),
                {"user_id": user_id},
            )
            conn.execute(
                sa.text(
                    "INSERT INTO org_organizations (id, code, name) VALUES (:id, 'MI-DEMO-ORG', 'Demo org')"
                ),
                {"id": uuid.uuid4()},
            )
            roles_before = conn.execute(sa.text("SELECT count(*) FROM security_roles")).scalar_one()
            perms_before = conn.execute(sa.text("SELECT count(*) FROM security_permissions")).scalar_one()
            audit_before = conn.execute(sa.text("SELECT count(*) FROM security_audit_log")).scalar_one()

        removed = purge(engine)
        assert removed["org_organizations"] == 1

        with engine.begin() as conn:
            assert sum(count_domain_rows(conn).values()) == 0
            assert conn.execute(sa.text("SELECT count(*) FROM security_users")).scalar_one() == 1
            assert conn.execute(sa.text("SELECT count(*) FROM security_user_roles")).scalar_one() == 1
            assert conn.execute(sa.text("SELECT count(*) FROM security_roles")).scalar_one() == roles_before
            assert (
                conn.execute(sa.text("SELECT count(*) FROM security_permissions")).scalar_one()
                == perms_before
            )
            audit_rows = conn.execute(
                sa.text("SELECT action, before_state FROM security_audit_log ORDER BY created_at")
            ).all()
            assert len(audit_rows) == audit_before + 1
            assert audit_rows[-1].action == AUDIT_ACTION
            assert audit_rows[-1].before_state["rows"]["org_organizations"] == 1

        # A second purge on empty tables is a no-op, not an error.
        purge(engine)
    finally:
        engine.dispose()
        alembic_command.downgrade(cfg, "base")
