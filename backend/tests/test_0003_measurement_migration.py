from __future__ import annotations

import hashlib
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
def test_measurement_migration_constraints() -> None:
    cfg = alembic_config.Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    engine = sa.create_engine(TEST_DATABASE_URL)

    try:
        alembic_command.upgrade(cfg, "head")

        with engine.begin() as connection:
            # --- catalog fixtures (0002) ---
            family_id = uuid.uuid4()
            part_id = uuid.uuid4()
            classification_id = uuid.uuid4()
            characteristic_id = uuid.uuid4()
            specification_id = uuid.uuid4()
            program_id = uuid.uuid4()

            connection.execute(
                sa.text(
                    "INSERT INTO catalog_product_families (id, code, name) "
                    "VALUES (:id, 'MI-DEMO-FAM-001', 'Demo family')"
                ),
                {"id": family_id},
            )
            connection.execute(
                sa.text(
                    "INSERT INTO catalog_part_numbers (id, product_family_id, code, name) "
                    "VALUES (:id, :family_id, 'MI-DEMO-PN-001', 'Demo part')"
                ),
                {"id": part_id, "family_id": family_id},
            )
            connection.execute(
                sa.text(
                    "INSERT INTO catalog_characteristic_classifications (id, code, name) "
                    "VALUES (:id, 'critical', 'Critical')"
                ),
                {"id": classification_id},
            )
            connection.execute(
                sa.text(
                    """
                    INSERT INTO catalog_characteristics (
                        id, part_number_id, balloon_number, name,
                        characteristic_type, unit, classification_id
                    )
                    VALUES (
                        :id, :part_id, '1', 'Bore diameter', 'diameter', 'mm', :classification_id
                    )
                    """
                ),
                {
                    "id": characteristic_id,
                    "part_id": part_id,
                    "classification_id": classification_id,
                },
            )
            connection.execute(
                sa.text(
                    """
                    INSERT INTO catalog_specifications (
                        id, characteristic_id, nominal, lower_tol, upper_tol, unit
                    )
                    VALUES (:id, :characteristic_id, 10.000, 0.050, 0.050, 'mm')
                    """
                ),
                {"id": specification_id, "characteristic_id": characteristic_id},
            )
            connection.execute(
                sa.text(
                    """
                    INSERT INTO catalog_measurement_programs (
                        id, part_number_id, name, output_mapping
                    )
                    VALUES (:id, :part_id, 'Demo program', '{}'::jsonb)
                    """
                ),
                {"id": program_id, "part_id": part_id},
            )

            # --- measurement fixtures (0003) ---
            connector_id = uuid.uuid4()
            data_source_id = uuid.uuid4()
            imported_file_id = uuid.uuid4()
            run_id = uuid.uuid4()
            sample_id = uuid.uuid4()

            connection.execute(
                sa.text(
                    "INSERT INTO measurement_connectors (id, code, name, connector_type) "
                    "VALUES (:id, 'manual', 'Manual upload', 'manual_upload')"
                ),
                {"id": connector_id},
            )
            connection.execute(
                sa.text(
                    "INSERT INTO measurement_data_sources (id, connector_id, code, name) "
                    "VALUES (:id, :connector_id, 'line-3-cmm', 'Line 3 CMM')"
                ),
                {"id": data_source_id, "connector_id": connector_id},
            )
            file_hash = hashlib.sha256(b"demo file contents").hexdigest()
            connection.execute(
                sa.text(
                    """
                    INSERT INTO measurement_imported_files (
                        id, data_source_id, object_key, original_filename, sha256, size_bytes
                    )
                    VALUES (
                        :id, :data_source_id, 'raw/2026/07/demo.csv', 'demo.csv', :sha256, 1024
                    )
                    """
                ),
                {"id": imported_file_id, "data_source_id": data_source_id, "sha256": file_hash},
            )

            # Duplicate content (same sha256) must be rejected — dedup.
            savepoint = connection.begin_nested()
            with pytest.raises(sa.exc.DBAPIError):
                connection.execute(
                    sa.text(
                        """
                        INSERT INTO measurement_imported_files (
                            id, data_source_id, object_key, original_filename, sha256, size_bytes
                        )
                        VALUES (
                            :id, :data_source_id, 'raw/2026/07/demo-copy.csv', 'demo-copy.csv', :sha256, 1024
                        )
                        """
                    ),
                    {"id": uuid.uuid4(), "data_source_id": data_source_id, "sha256": file_hash},
                )
            savepoint.rollback()

            connection.execute(
                sa.text(
                    """
                    INSERT INTO measurement_runs (
                        id, part_number_id, measurement_program_id, data_source_id,
                        imported_file_id, started_at
                    )
                    VALUES (
                        :id, :part_id, :program_id, :data_source_id, :imported_file_id, now()
                    )
                    """
                ),
                {
                    "id": run_id,
                    "part_id": part_id,
                    "program_id": program_id,
                    "data_source_id": data_source_id,
                    "imported_file_id": imported_file_id,
                },
            )
            connection.execute(
                sa.text(
                    "INSERT INTO measurement_samples (id, measurement_run_id, sample_index) "
                    "VALUES (:id, :run_id, 1)"
                ),
                {"id": sample_id, "run_id": run_id},
            )

            # --- results spanning two monthly partitions ---
            result_jan_id = uuid.uuid4()
            result_jul_id = uuid.uuid4()
            connection.execute(
                sa.text(
                    """
                    INSERT INTO measurement_results (
                        id, measurement_sample_id, characteristic_id, specification_id,
                        value, deviation, is_ok, measured_at
                    )
                    VALUES (
                        :id, :sample_id, :characteristic_id, :specification_id,
                        10.010, 0.010, true, '2026-01-15 10:00:00+00'
                    )
                    """
                ),
                {
                    "id": result_jan_id,
                    "sample_id": sample_id,
                    "characteristic_id": characteristic_id,
                    "specification_id": specification_id,
                },
            )
            connection.execute(
                sa.text(
                    """
                    INSERT INTO measurement_results (
                        id, measurement_sample_id, characteristic_id, specification_id,
                        value, deviation, is_ok, measured_at
                    )
                    VALUES (
                        :id, :sample_id, :characteristic_id, :specification_id,
                        10.045, 0.045, true, '2026-07-15 10:00:00+00'
                    )
                    """
                ),
                {
                    "id": result_jul_id,
                    "sample_id": sample_id,
                    "characteristic_id": characteristic_id,
                    "specification_id": specification_id,
                },
            )

            # Rows landed in the expected monthly partitions.
            partitions = dict(
                connection.execute(
                    sa.text(
                        "SELECT id, tableoid::regclass::text FROM measurement_results "
                        "WHERE id IN (:jan, :jul)"
                    ),
                    {"jan": result_jan_id, "jul": result_jul_id},
                ).all()
            )
            assert partitions[result_jan_id] == "measurement_results_2026_01"
            assert partitions[result_jul_id] == "measurement_results_2026_07"

            # A result outside the explicit monthly range falls into DEFAULT.
            result_default_id = uuid.uuid4()
            connection.execute(
                sa.text(
                    """
                    INSERT INTO measurement_results (
                        id, measurement_sample_id, characteristic_id, specification_id,
                        value, deviation, is_ok, measured_at
                    )
                    VALUES (
                        :id, :sample_id, :characteristic_id, :specification_id,
                        10.020, 0.020, true, '2030-01-01 00:00:00+00'
                    )
                    """
                ),
                {
                    "id": result_default_id,
                    "sample_id": sample_id,
                    "characteristic_id": characteristic_id,
                    "specification_id": specification_id,
                },
            )
            default_partition = connection.execute(
                sa.text(
                    "SELECT tableoid::regclass::text FROM measurement_results WHERE id = :id"
                ),
                {"id": result_default_id},
            ).scalar_one()
            assert default_partition == "measurement_results_default"

            # Time-series query crossing partitions returns rows in order.
            series = connection.execute(
                sa.text(
                    "SELECT id FROM measurement_results "
                    "WHERE characteristic_id = :characteristic_id AND measured_at < '2029-01-01' "
                    "ORDER BY measured_at"
                ),
                {"characteristic_id": characteristic_id},
            ).scalars().all()
            assert series == [result_jan_id, result_jul_id]

            # Immutability: UPDATE and DELETE are rejected regardless of caller.
            savepoint = connection.begin_nested()
            with pytest.raises(sa.exc.DBAPIError):
                connection.execute(
                    sa.text("UPDATE measurement_results SET value = 99.999 WHERE id = :id"),
                    {"id": result_jan_id},
                )
            savepoint.rollback()

            savepoint = connection.begin_nested()
            with pytest.raises(sa.exc.DBAPIError):
                connection.execute(
                    sa.text("DELETE FROM measurement_results WHERE id = :id"),
                    {"id": result_jan_id},
                )
            savepoint.rollback()
    finally:
        engine.dispose()
        alembic_command.downgrade(cfg, "base")
