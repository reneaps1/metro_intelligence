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
def test_catalog_migration_constraints() -> None:
    cfg = alembic_config.Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    engine = sa.create_engine(TEST_DATABASE_URL)

    try:
        alembic_command.upgrade(cfg, "head")

        with engine.begin() as connection:
            family_id = uuid.uuid4()
            part_id = uuid.uuid4()
            classification_id = uuid.uuid4()
            characteristic_id = uuid.uuid4()

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

            # Balloon number unique per part.
            savepoint = connection.begin_nested()
            with pytest.raises(sa.exc.DBAPIError):
                connection.execute(
                    sa.text(
                        """
                        INSERT INTO catalog_characteristics (
                            id, part_number_id, balloon_number, name,
                            characteristic_type, unit, classification_id
                        )
                        VALUES (
                            :id, :part_id, '1', 'Duplicate balloon',
                            'diameter', 'mm', :classification_id
                        )
                        """
                    ),
                    {
                        "id": uuid.uuid4(),
                        "part_id": part_id,
                        "classification_id": classification_id,
                    },
                )
            savepoint.rollback()

            # Unilateral tolerance (upper only) is representable.
            connection.execute(
                sa.text(
                    """
                    INSERT INTO catalog_specifications (
                        id, characteristic_id, nominal, lower_tol, upper_tol, unit
                    )
                    VALUES (:id, :characteristic_id, 10.000, NULL, 0.050, 'mm')
                    """
                ),
                {"id": uuid.uuid4(), "characteristic_id": characteristic_id},
            )

            # A second active (valid_to IS NULL) specification for the same
            # characteristic must be rejected.
            savepoint = connection.begin_nested()
            with pytest.raises(sa.exc.DBAPIError):
                connection.execute(
                    sa.text(
                        """
                        INSERT INTO catalog_specifications (
                            id, characteristic_id, nominal, lower_tol, upper_tol, unit
                        )
                        VALUES (:id, :characteristic_id, 10.000, 0.050, 0.050, 'mm')
                        """
                    ),
                    {"id": uuid.uuid4(), "characteristic_id": characteristic_id},
                )
            savepoint.rollback()

            # A specification with neither tolerance bound is meaningless and rejected.
            savepoint = connection.begin_nested()
            with pytest.raises(sa.exc.DBAPIError):
                connection.execute(
                    sa.text(
                        """
                        INSERT INTO catalog_specifications (
                            id, characteristic_id, nominal, lower_tol, upper_tol, unit, valid_to
                        )
                        VALUES (
                            :id, :characteristic_id, 10.000, NULL, NULL, 'mm', now() + interval '1 day'
                        )
                        """
                    ),
                    {"id": uuid.uuid4(), "characteristic_id": characteristic_id},
                )
            savepoint.rollback()
    finally:
        engine.dispose()
        alembic_command.downgrade(cfg, "base")
