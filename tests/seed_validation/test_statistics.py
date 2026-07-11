"""F3.5 (MI-20): statistical sanity over the full generated dataset --
generated Cpk/behavior per scenario must match the label the seed assigned
it (docs/seed-data-strategy.md), checked across *every* characteristic of
that scenario type, not just one sample (seed/tests/test_measurement_series_generator.py
already covers a single representative characteristic per scenario at the
generator-unit level).

Needs a disposable PostgreSQL database (METRO_TEST_DATABASE_URL); skipped
otherwise.
"""
from __future__ import annotations

from datetime import timedelta

import numpy as np
import sqlalchemy as sa

from .conftest import requires_database


def _characteristic_values(connection, characteristic_id) -> np.ndarray:
    values = connection.execute(
        sa.text("SELECT value FROM measurement_results WHERE characteristic_id = :cid"),
        {"cid": characteristic_id},
    ).scalars().all()
    return np.array([float(v) for v in values])


def _active_spec(connection, characteristic_id) -> tuple[float, float | None, float | None]:
    nominal, lower_tol, upper_tol = connection.execute(
        sa.text(
            "SELECT nominal, lower_tol, upper_tol FROM catalog_specifications "
            "WHERE characteristic_id = :cid AND valid_to IS NULL"
        ),
        {"cid": characteristic_id},
    ).one()
    return (
        float(nominal),
        float(lower_tol) if lower_tol is not None else None,
        float(upper_tol) if upper_tol is not None else None,
    )


def _cpk(values: np.ndarray, nominal: float, lower_tol: float | None, upper_tol: float | None) -> float:
    mean, std = values.mean(), values.std()
    if std == 0:
        return float("inf")
    upper_cpk = (nominal + upper_tol - mean) / (3 * std) if upper_tol is not None else float("inf")
    lower_cpk = (mean - (nominal + lower_tol)) / (3 * std) if lower_tol is not None else float("inf")
    return min(upper_cpk, lower_cpk)


@requires_database
def test_dataset_size_and_generation_performance(seeded_engine) -> None:
    engine, context = seeded_engine
    with engine.begin() as connection:
        total = connection.execute(sa.text("SELECT count(*) FROM measurement_results")).scalar_one()
    assert total > 50_000
    assert total == context.artifacts["measurement_result_count"]


@requires_database
def test_all_scenarios_are_represented(seeded_engine) -> None:
    _engine, context = seeded_engine
    scenario_by_characteristic_id = context.artifacts["scenario_by_characteristic_id"]
    assert set(scenario_by_characteristic_id.values()) == {
        "stable_capable",
        "slow_drift",
        "shift_after_event",
        "high_variance",
        "outlier_nok",
    }


@requires_database
def test_stable_capable_characteristics_are_reliably_capable(seeded_engine) -> None:
    engine, context = seeded_engine
    scenario_by_characteristic_id = context.artifacts["scenario_by_characteristic_id"]
    stable_ids = [cid for cid, name in scenario_by_characteristic_id.items() if name == "stable_capable"]
    assert stable_ids

    with engine.begin() as connection:
        for characteristic_id in stable_ids:
            values = _characteristic_values(connection, characteristic_id)
            nominal, lower_tol, upper_tol = _active_spec(connection, characteristic_id)
            cpk = _cpk(values, nominal, lower_tol, upper_tol)
            assert cpk > 1.33, f"stable_capable characteristic {characteristic_id} has Cpk={cpk:.2f}"


@requires_database
def test_high_variance_characteristics_are_marginally_capable_or_worse(seeded_engine) -> None:
    engine, context = seeded_engine
    scenario_by_characteristic_id = context.artifacts["scenario_by_characteristic_id"]
    high_variance_ids = [cid for cid, name in scenario_by_characteristic_id.items() if name == "high_variance"]
    assert high_variance_ids

    with engine.begin() as connection:
        for characteristic_id in high_variance_ids:
            values = _characteristic_values(connection, characteristic_id)
            nominal, lower_tol, upper_tol = _active_spec(connection, characteristic_id)
            cpk = _cpk(values, nominal, lower_tol, upper_tol)
            assert cpk < 1.33, f"high_variance characteristic {characteristic_id} has Cpk={cpk:.2f}"


@requires_database
def test_slow_drift_characteristics_cross_the_limit_by_the_end_of_history(seeded_engine) -> None:
    engine, context = seeded_engine
    scenario_by_characteristic_id = context.artifacts["scenario_by_characteristic_id"]
    drift_ids = [cid for cid, name in scenario_by_characteristic_id.items() if name == "slow_drift"]
    assert drift_ids

    with engine.begin() as connection:
        for characteristic_id in drift_ids:
            nok_recent = connection.execute(
                sa.text(
                    """
                    SELECT count(*) FROM measurement_results
                    WHERE characteristic_id = :cid
                      AND is_ok = false
                      AND measured_at >= now() - interval '15 days'
                    """
                ),
                {"cid": characteristic_id},
            ).scalar_one()
            assert nok_recent > 0, f"slow_drift characteristic {characteristic_id} never crosses the limit"


@requires_database
def test_outlier_nok_characteristics_are_mostly_ok_but_not_exclusively(seeded_engine) -> None:
    engine, context = seeded_engine
    scenario_by_characteristic_id = context.artifacts["scenario_by_characteristic_id"]
    outlier_ids = [cid for cid, name in scenario_by_characteristic_id.items() if name == "outlier_nok"]
    assert outlier_ids

    with engine.begin() as connection:
        for characteristic_id in outlier_ids:
            ok_count, nok_count = connection.execute(
                sa.text(
                    """
                    SELECT count(*) FILTER (WHERE is_ok), count(*) FILTER (WHERE NOT is_ok)
                    FROM measurement_results WHERE characteristic_id = :cid
                    """
                ),
                {"cid": characteristic_id},
            ).one()
            assert nok_count > 0, f"outlier_nok characteristic {characteristic_id} has no NOK results"
            assert ok_count > nok_count, f"outlier_nok characteristic {characteristic_id} is mostly NOK"


@requires_database
def test_shift_after_event_characteristics_shift_mean_after_the_event_day(seeded_engine) -> None:
    engine, context = seeded_engine
    scenario_by_characteristic_id = context.artifacts["scenario_by_characteristic_id"]
    shift_ids = [cid for cid, name in scenario_by_characteristic_id.items() if name == "shift_after_event"]
    assert shift_ids

    start_day = context.artifacts["history_start_day"]
    shift_event_day = context.config.scenario("shift_after_event").event_day_offset or 0

    with engine.begin() as connection:
        for characteristic_id in shift_ids:
            before, after = connection.execute(
                sa.text(
                    """
                    SELECT
                        avg(deviation) FILTER (WHERE measured_at < :event_day),
                        avg(deviation) FILTER (WHERE measured_at >= :event_day)
                    FROM measurement_results WHERE characteristic_id = :cid
                    """
                ),
                {"cid": characteristic_id, "event_day": start_day + timedelta(days=shift_event_day)},
            ).one()
            assert before is not None and after is not None
            assert abs(float(after)) > abs(float(before)), (
                f"shift_after_event characteristic {characteristic_id} shows no mean shift after the event day"
            )
