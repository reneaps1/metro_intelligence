"""Migration 0009: process tables, optional specification, 2025 partitions,
process read permission for every role; clean downgrade."""

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
PROCESS_TABLES = {
    "process_operations",
    "process_recipes",
    "process_part_instances",
    "process_step_results",
    "process_step_daily",
    "process_characteristic_daily",
    "process_stats_builds",
}


def _config() -> alembic_config.Config:
    cfg = alembic_config.Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return cfg


def _insert_result_chain(conn: sa.Connection, measured_at: str) -> None:
    """Minimal org/catalog/measurement chain ending in one result without spec."""
    ids = {
        name: uuid.uuid4()
        for name in ("org", "site", "area", "line", "fam", "part", "cls", "char", "prog", "run", "sample")
    }
    statements = [
        ("INSERT INTO org_organizations (id, code, name) VALUES (:org, 'MI-DEMO-ORG', 'Org')", {}),
        (
            "INSERT INTO org_sites (id, organization_id, code, name, timezone) VALUES (:site, :org, 'S', 'S', 'UTC')",
            {},
        ),
        ("INSERT INTO org_areas (id, site_id, code, name) VALUES (:area, :site, 'A', 'A')", {}),
        ("INSERT INTO org_lines (id, area_id, code, name) VALUES (:line, :area, 'L', 'L')", {}),
        ("INSERT INTO catalog_product_families (id, code, name) VALUES (:fam, 'F', 'F')", {}),
        (
            "INSERT INTO catalog_part_numbers (id, product_family_id, code, name) VALUES (:part, :fam, 'MI-DEMO-1', 'P')",
            {},
        ),
        (
            "INSERT INTO catalog_characteristic_classifications (id, code, name) VALUES (:cls, 'standard', 'Standard')",
            {},
        ),
        (
            "INSERT INTO catalog_characteristics (id, part_number_id, balloon_number, name, characteristic_type, unit, "
            "classification_id) VALUES (:char, :part, 1, 'Ref', 'length', 'mm', :cls)",
            {},
        ),
        (
            "INSERT INTO catalog_measurement_programs (id, part_number_id, name, version, output_mapping, valid_from) "
            "VALUES (:prog, :part, 'P', '1', '{}'::jsonb, now())",
            {},
        ),
        ("INSERT INTO measurement_runs (id, measurement_program_id, run_at) VALUES (:run, :prog, :at)", {}),
        (
            "INSERT INTO measurement_samples (id, measurement_run_id, sample_sequence) VALUES (:sample, :run, 1)",
            {},
        ),
        (
            "INSERT INTO measurement_results (id, measured_at, measurement_sample_id, characteristic_id, value, "
            "machine_ok, machine_code) VALUES (gen_random_uuid(), :at, :sample, :char, 0.123456789, true, 4)",
            {},
        ),
    ]
    for sql, extra in statements:
        conn.execute(sa.text(sql), {**ids, "at": measured_at, **extra})


@pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="Set METRO_TEST_DATABASE_URL to a disposable PostgreSQL database."
)
def test_process_model_migration_upgrade_and_downgrade() -> None:
    cfg = _config()
    engine = sa.create_engine(TEST_DATABASE_URL)
    try:
        alembic_command.upgrade(cfg, "head")
        inspector = sa.inspect(engine)
        assert PROCESS_TABLES <= set(inspector.get_table_names())

        with engine.begin() as conn:
            _insert_result_chain(conn, "2025-06-15T08:00:00+00:00")
            partition = conn.execute(
                sa.text("SELECT tableoid::regclass::text, value FROM measurement_results")
            ).one()
            assert partition[0] == "measurement_results_2025_06"
            assert str(partition[1]) == "0.123456789"

            granted = set(
                conn.execute(
                    sa.text(
                        "SELECT r.name FROM security_roles r "
                        "JOIN security_role_permissions rp ON rp.role_id = r.id "
                        "JOIN security_permissions p ON p.id = rp.permission_id "
                        "WHERE p.token = 'process.operation.read'"
                    )
                ).scalars()
            )
            assert granted == {"viewer", "metrologist", "quality_engineer", "admin", "auditor"}

            conn.execute(
                sa.text("TRUNCATE measurement_results, measurement_samples, measurement_runs CASCADE")
            )

        alembic_command.downgrade(cfg, "0008_alarm_alerts")
        assert not PROCESS_TABLES & set(sa.inspect(engine).get_table_names())
    finally:
        engine.dispose()
        alembic_command.downgrade(cfg, "base")
