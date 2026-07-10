from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
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
def test_measurement_migration_partitioning_and_immutability() -> None:
    cfg = alembic_config.Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    engine = sa.create_engine(TEST_DATABASE_URL)

    try:
        alembic_command.upgrade(cfg, "head")

        with engine.begin() as connection:
            # ---- catalog fixtures (F2.2) ----
            family_id = uuid.uuid4()
            part_id = uuid.uuid4()
            classification_id = uuid.uuid4()
            characteristic_id = uuid.uuid4()
            specification_id = uuid.uuid4()
            program_id = uuid.uuid4()

            connection.execute(
                sa.text(
                    "INSERT INTO catalog_product_families (id, code, name) "
                    "VALUES (:id, 'MI-DEMO-FAM-010', 'Demo family')"
                ),
                {"id": family_id},
            )
            connection.execute(
                sa.text(
                    "INSERT INTO catalog_part_numbers (id, product_family_id, code, name) "
                    "VALUES (:id, :family_id, 'MI-DEMO-PN-010', 'Demo part')"
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
                    VALUES (:id, :part_id, '1', 'Bore diameter', 'diameter', 'mm', :classification_id)
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
                        id, part_number_id, name, version, output_mapping
                    )
                    VALUES (:id, :part_id, 'Program A', 1, '{}'::jsonb)
                    """
                ),
                {"id": program_id, "part_id": part_id},
            )

            # ---- measurement fixtures ----
            data_source_id = uuid.uuid4()
            imported_file_id = uuid.uuid4()
            run_id = uuid.uuid4()
            sample_id = uuid.uuid4()

            connection.execute(
                sa.text(
                    "INSERT INTO measurement_data_sources (id, code, name, source_type) "
                    "VALUES (:id, 'manual-upload', 'Manual upload', 'manual_upload')"
                ),
                {"id": data_source_id},
            )
            connection.execute(
                sa.text(
                    """
                    INSERT INTO measurement_imported_files (
                        id, data_source_id, original_filename, storage_bucket,
                        storage_object_key, sha256, size_bytes, parse_status
                    )
                    VALUES (
                        :id, :data_source_id, 'run1.csv', 'raw-imports',
                        'raw-imports/run1.csv', :sha256, 1024, 'parsed'
                    )
                    """
                ),
                {"id": imported_file_id, "data_source_id": data_source_id, "sha256": "a" * 64},
            )

            # dedup by hash: a second file with the same sha256 must be rejected.
            savepoint = connection.begin_nested()
            with pytest.raises(sa.exc.DBAPIError):
                connection.execute(
                    sa.text(
                        """
                        INSERT INTO measurement_imported_files (
                            id, data_source_id, original_filename, storage_bucket,
                            storage_object_key, sha256, size_bytes, parse_status
                        )
                        VALUES (
                            :id, :data_source_id, 'run1-copy.csv', 'raw-imports',
                            'raw-imports/run1-copy.csv', :sha256, 1024, 'parsed'
                        )
                        """
                    ),
                    {"id": uuid.uuid4(), "data_source_id": data_source_id, "sha256": "a" * 64},
                )
            savepoint.rollback()

            connection.execute(
                sa.text(
                    """
                    INSERT INTO measurement_runs (id, measurement_program_id, imported_file_id, run_at)
                    VALUES (:id, :program_id, :imported_file_id, now())
                    """
                ),
                {"id": run_id, "program_id": program_id, "imported_file_id": imported_file_id},
            )
            connection.execute(
                sa.text(
                    "INSERT INTO measurement_samples (id, measurement_run_id, sample_sequence) "
                    "VALUES (:id, :run_id, 1)"
                ),
                {"id": sample_id, "run_id": run_id},
            )

            # two results in different months -> different partitions
            result_march_id = uuid.uuid4()
            result_july_id = uuid.uuid4()
            march_ts = datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc)
            july_ts = datetime(2026, 7, 15, 10, 0, tzinfo=timezone.utc)

            for rid, ts, value in [(result_march_id, march_ts, 10.02), (result_july_id, july_ts, 10.03)]:
                connection.execute(
                    sa.text(
                        """
                        INSERT INTO measurement_results (
                            id, measured_at, measurement_sample_id, characteristic_id,
                            specification_id, value, deviation, is_ok
                        )
                        VALUES (
                            :id, :measured_at, :sample_id, :characteristic_id,
                            :specification_id, :value, :value - 10.0, true
                        )
                        """
                    ),
                    {
                        "id": rid,
                        "measured_at": ts,
                        "sample_id": sample_id,
                        "characteristic_id": characteristic_id,
                        "specification_id": specification_id,
                        "value": value,
                    },
                )

            # specification_id is mandatory.
            savepoint = connection.begin_nested()
            with pytest.raises(sa.exc.DBAPIError):
                connection.execute(
                    sa.text(
                        """
                        INSERT INTO measurement_results (
                            id, measured_at, measurement_sample_id, characteristic_id, value
                        )
                        VALUES (:id, now(), :sample_id, :characteristic_id, 10.0)
                        """
                    ),
                    {"id": uuid.uuid4(), "sample_id": sample_id, "characteristic_id": characteristic_id},
                )
            savepoint.rollback()

            # partitioning is functional: each row lives in its month's partition.
            march_partition = connection.execute(
                sa.text("SELECT tableoid::regclass::text FROM measurement_results WHERE id = :id"),
                {"id": result_march_id},
            ).scalar_one()
            july_partition = connection.execute(
                sa.text("SELECT tableoid::regclass::text FROM measurement_results WHERE id = :id"),
                {"id": result_july_id},
            ).scalar_one()
            assert march_partition == "measurement_results_2026_03"
            assert july_partition == "measurement_results_2026_07"

            # a time-series query must transparently cross partitions.
            series = connection.execute(
                sa.text(
                    """
                    SELECT value FROM measurement_results
                    WHERE characteristic_id = :characteristic_id
                    ORDER BY measured_at
                    """
                ),
                {"characteristic_id": characteristic_id},
            ).scalars().all()
            assert [float(v) for v in series] == [10.02, 10.03]

            # immutability: UPDATE fails even though the row exists and matches.
            savepoint = connection.begin_nested()
            with pytest.raises(sa.exc.DBAPIError):
                connection.execute(
                    sa.text("UPDATE measurement_results SET value = 99.0 WHERE id = :id"),
                    {"id": result_march_id},
                )
            savepoint.rollback()

            # immutability: DELETE also fails.
            savepoint = connection.begin_nested()
            with pytest.raises(sa.exc.DBAPIError):
                connection.execute(
                    sa.text("DELETE FROM measurement_results WHERE id = :id"),
                    {"id": result_march_id},
                )
            savepoint.rollback()

            # a correction is a new row referencing supersedes_id, not a mutation.
            correction_id = uuid.uuid4()
            connection.execute(
                sa.text(
                    """
                    INSERT INTO measurement_results (
                        id, measured_at, measurement_sample_id, characteristic_id,
                        specification_id, value, deviation, is_ok, supersedes_id
                    )
                    VALUES (
                        :id, :measured_at, :sample_id, :characteristic_id,
                        :specification_id, 10.021, 0.021, true, :supersedes_id
                    )
                    """
                ),
                {
                    "id": correction_id,
                    "measured_at": march_ts,
                    "sample_id": sample_id,
                    "characteristic_id": characteristic_id,
                    "specification_id": specification_id,
                    "supersedes_id": result_march_id,
                },
            )
    finally:
        engine.dispose()
        alembic_command.downgrade(cfg, "base")
