from __future__ import annotations

import os
from pathlib import Path

import pytest

alembic_command = pytest.importorskip("alembic.command")
alembic_config = pytest.importorskip("alembic.config")
sa = pytest.importorskip("sqlalchemy")

from seed.db import get_session  # noqa: E402
from seed.generators.base import SeedContext, make_rng  # noqa: E402
from seed.generators.catalog import generate_catalog  # noqa: E402
from seed.config import load_config  # noqa: E402

TEST_DATABASE_URL = os.getenv("METRO_TEST_DATABASE_URL")
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"


@pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set METRO_TEST_DATABASE_URL to a disposable PostgreSQL database.",
)
def test_catalog_generator_satisfies_acceptance_criteria() -> None:
    cfg = alembic_config.Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    engine = sa.create_engine(TEST_DATABASE_URL)
    try:
        alembic_command.upgrade(cfg, "head")

        session = get_session(engine)
        context = SeedContext(session=session, rng=make_rng(20260709), config=load_config())
        try:
            generate_catalog(context)
            session.commit()
        except Exception:
            session.rollback()
            raise

        with engine.begin() as connection:
            # 3 families, 8 parts.
            assert connection.execute(sa.text("SELECT count(*) FROM catalog_product_families")).scalar_one() == 3
            assert connection.execute(sa.text("SELECT count(*) FROM catalog_part_numbers")).scalar_one() == 8

            # Balloon numbers unique per part (DB constraint enforced this already
            # by not raising above; assert count matches distinct pairs too).
            total_chars, distinct_pairs = connection.execute(
                sa.text(
                    "SELECT count(*), count(DISTINCT (part_number_id, balloon_number)) FROM catalog_characteristics"
                )
            ).one()
            assert total_chars == distinct_pairs
            assert 80 <= total_chars <= 200  # 8 parts x 10-25 characteristics

            # Every part has at least one critical (CC) characteristic.
            parts_missing_cc = connection.execute(
                sa.text(
                    """
                    SELECT count(*) FROM catalog_part_numbers p
                    WHERE NOT EXISTS (
                        SELECT 1 FROM catalog_characteristics c
                        JOIN catalog_characteristic_classifications cl ON cl.id = c.classification_id
                        WHERE c.part_number_id = p.id AND cl.code = 'critical'
                    )
                    """
                )
            ).scalar_one()
            assert parts_missing_cc == 0

            # Every specification is internally consistent: lower_tol < upper_tol
            # when both present, and at least one bound present.
            bad_specs = connection.execute(
                sa.text(
                    """
                    SELECT count(*) FROM catalog_specifications
                    WHERE (lower_tol IS NULL AND upper_tol IS NULL)
                       OR (lower_tol IS NOT NULL AND upper_tol IS NOT NULL AND lower_tol >= upper_tol)
                    """
                )
            ).scalar_one()
            assert bad_specs == 0

            # Spec versioning demo: at least one characteristic has 2+ specs.
            versioned_count = connection.execute(
                sa.text(
                    """
                    SELECT count(*) FROM (
                        SELECT characteristic_id FROM catalog_specifications
                        GROUP BY characteristic_id HAVING count(*) > 1
                    ) t
                    """
                )
            ).scalar_one()
            assert versioned_count >= 1

            # Demo plant: 1 org, 1 site, 3 lines, 3 machines (2 CMM + 1 scanner).
            assert connection.execute(sa.text("SELECT count(*) FROM org_lines")).scalar_one() == 3
            machine_types = connection.execute(sa.text("SELECT machine_type FROM org_machines")).scalars().all()
            assert sorted(machine_types) == ["CMM", "CMM", "scanner"]

            # No identifiers resembling real customer data (CLAUDE.md §20/§7)
            # — a light gut-check; the full lint suite is F3.5.
            codes = connection.execute(sa.text("SELECT code FROM catalog_part_numbers")).scalars().all()
            assert all(code.startswith("MI-DEMO-") for code in codes)
    finally:
        engine.dispose()
        alembic_command.downgrade(cfg, "base")
