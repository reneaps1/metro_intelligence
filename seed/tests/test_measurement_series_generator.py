from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

alembic_command = pytest.importorskip("alembic.command")
alembic_config = pytest.importorskip("alembic.config")
sa = pytest.importorskip("sqlalchemy")
np = pytest.importorskip("numpy")

from seed.config import load_config  # noqa: E402
from seed.db import get_session  # noqa: E402
from seed.generators.base import SeedContext, make_rng  # noqa: E402
from seed.generators.catalog import generate_catalog  # noqa: E402
from seed.generators.measurements import generate_measurement_series  # noqa: E402

TEST_DATABASE_URL = os.getenv("METRO_TEST_DATABASE_URL")
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"


@pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set METRO_TEST_DATABASE_URL to a disposable PostgreSQL database.",
)
def test_measurement_series_matches_scenario_behavior_and_perf() -> None:
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
            start = time.monotonic()
            generate_measurement_series(context)
            elapsed = time.monotonic() - start
            session.commit()
        except Exception:
            session.rollback()
            raise

        assert context.artifacts["measurement_result_count"] > 50_000
        assert elapsed < 120, f"measurement generation took {elapsed:.1f}s, expected < 120s"

        scenario_by_characteristic_id = context.artifacts["scenario_by_characteristic_id"]
        assert set(scenario_by_characteristic_id.values()) == {
            "stable_capable",
            "slow_drift",
            "shift_after_event",
            "high_variance",
            "outlier_nok",
        }

        with engine.begin() as connection:
            total = connection.execute(sa.text("SELECT count(*) FROM measurement_results")).scalar_one()
            assert total == context.artifacts["measurement_result_count"]

            # stable_capable: reliably capable (Cpk well above 1.33) given its
            # tight noise_std_fraction_of_tolerance in scenarios.yaml.
            stable_id = next(
                cid for cid, name in scenario_by_characteristic_id.items() if name == "stable_capable"
            )
            values = connection.execute(
                sa.text("SELECT value FROM measurement_results WHERE characteristic_id = :cid"),
                {"cid": stable_id},
            ).scalars().all()
            spec_row = connection.execute(
                sa.text(
                    "SELECT nominal, lower_tol, upper_tol FROM catalog_specifications "
                    "WHERE characteristic_id = :cid AND valid_to IS NULL"
                ),
                {"cid": stable_id},
            ).one()
            nominal = float(spec_row[0])
            lower_tol = float(spec_row[1]) if spec_row[1] is not None else None
            upper_tol = float(spec_row[2]) if spec_row[2] is not None else None
            arr = np.array([float(v) for v in values])
            mean, std = arr.mean(), arr.std()
            upper_cpk = (nominal + upper_tol - mean) / (3 * std) if upper_tol is not None else float("inf")
            lower_cpk = (mean - (nominal + lower_tol)) / (3 * std) if lower_tol is not None else float("inf")
            assert min(upper_cpk, lower_cpk) > 1.33

            # slow_drift: later samples (day >= 75) include NOK results —
            # the drift has visibly reached/crossed the limit by then.
            drift_id = next(cid for cid, name in scenario_by_characteristic_id.items() if name == "slow_drift")
            nok_after_day_75 = connection.execute(
                sa.text(
                    """
                    SELECT count(*) FROM measurement_results
                    WHERE characteristic_id = :cid
                      AND is_ok = false
                      AND measured_at >= now() - interval '15 days'
                    """
                ),
                {"cid": drift_id},
            ).scalar_one()
            assert nok_after_day_75 > 0

            # outlier_nok: mostly OK, but not exclusively.
            outlier_id = next(
                cid for cid, name in scenario_by_characteristic_id.items() if name == "outlier_nok"
            )
            ok_count, nok_count = connection.execute(
                sa.text(
                    """
                    SELECT count(*) FILTER (WHERE is_ok), count(*) FILTER (WHERE NOT is_ok)
                    FROM measurement_results WHERE characteristic_id = :cid
                    """
                ),
                {"cid": outlier_id},
            ).one()
            assert nok_count > 0
            assert ok_count > nok_count  # "occasional" outliers, not the norm
    finally:
        engine.dispose()
        alembic_command.downgrade(cfg, "base")
