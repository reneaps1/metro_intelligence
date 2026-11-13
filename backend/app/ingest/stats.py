"""Rebuild the derived daily statistics of a line (ADR-005).

Compliance is evaluated here against the specification version in force at
each result's `measured_at`, so importing a new specification version only
needs a rebuild: measurement results are never updated. Every column is
additive (counts, sums, min, max), so rows for the same day produced by two
month windows simply add up in queries.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import Connection, Engine, text

from app.models.base import uuid7

ENGINE_NAME = "process_daily_stats"
ENGINE_VERSION = "v1"

_SPEC_JOIN = """
    LEFT JOIN catalog_specifications s
      ON s.characteristic_id = r.characteristic_id
     AND r.measured_at >= s.valid_from
     AND (s.valid_to IS NULL OR r.measured_at < s.valid_to)
"""
_SPEC_NOK = (
    "(s.id IS NOT NULL AND NOT ((s.lower_tol IS NULL OR r.value - s.nominal >= s.lower_tol) "
    "AND (s.upper_tol IS NULL OR r.value - s.nominal <= s.upper_tol)))"
)

_INSERT_CHAR = f"""
INSERT INTO process_characteristic_daily (
    day, operation_id, recipe_id, nest, characteristic_id, specification_id,
    n, n_machine_nok, n_evaluated, n_spec_nok, n_machine_ok_spec_nok,
    sum_value, sum_sq_value, min_value, max_value)
SELECT (r.measured_at AT TIME ZONE :tz)::date, sr.operation_id, pi.recipe_id, sr.nest,
       r.characteristic_id, s.id,
       count(*),
       count(*) FILTER (WHERE r.machine_ok IS FALSE),
       count(s.id),
       count(*) FILTER (WHERE {_SPEC_NOK}),
       count(*) FILTER (WHERE r.machine_ok IS TRUE AND {_SPEC_NOK}),
       sum(r.value::float8), sum(r.value::float8 * r.value::float8),
       min(r.value::float8), max(r.value::float8)
FROM measurement_results r
JOIN process_step_results sr ON sr.measurement_sample_id = r.measurement_sample_id
JOIN process_part_instances pi ON pi.id = sr.part_instance_id
{_SPEC_JOIN}
WHERE r.measured_at >= :t0 AND r.measured_at < :t1 AND sr.operation_id = ANY(:ops)
GROUP BY 1, 2, 3, 4, 5, 6
"""

_INSERT_STEP = f"""
WITH spec_nok AS (
    SELECT DISTINCT r.measurement_sample_id
    FROM measurement_results r
    {_SPEC_JOIN}
    WHERE r.measured_at >= :t0 AND r.measured_at < :t1 AND {_SPEC_NOK}
)
INSERT INTO process_step_daily (
    day, operation_id, recipe_id, nest, pieces, pieces_machine_nok, pieces_spec_nok,
    first_attempt_ok, repeat_attempts)
SELECT (sr.recorded_at AT TIME ZONE :tz)::date, sr.operation_id, pi.recipe_id, sr.nest,
       count(*) FILTER (WHERE sr.attempt_no = 1),
       count(*) FILTER (WHERE sr.attempt_no = 1 AND sr.machine_ok IS FALSE),
       count(*) FILTER (WHERE sr.attempt_no = 1 AND b.measurement_sample_id IS NOT NULL),
       count(*) FILTER (WHERE sr.attempt_no = 1 AND sr.machine_ok IS TRUE),
       count(*) FILTER (WHERE sr.attempt_no > 1)
FROM process_step_results sr
JOIN process_part_instances pi ON pi.id = sr.part_instance_id
LEFT JOIN spec_nok b ON b.measurement_sample_id = sr.measurement_sample_id
WHERE sr.recorded_at >= :t0 AND sr.recorded_at < :t1 AND sr.operation_id = ANY(:ops)
GROUP BY 1, 2, 3, 4
"""


def _month_starts(first: datetime, last: datetime) -> list[datetime]:
    months = []
    current = datetime(first.year, first.month, 1, tzinfo=UTC)
    while current <= last:
        months.append(current)
        current = datetime(current.year + (current.month == 12), current.month % 12 + 1, 1, tzinfo=UTC)
    months.append(current)
    return months


def build_daily_stats(engine: Engine, line_id: uuid.UUID, tz: str) -> dict[str, int]:
    """Rebuild all daily rows of the line's operations. Returns row counts."""
    with engine.begin() as conn:
        ops = list(
            conn.execute(
                text("SELECT id FROM process_operations WHERE line_id = :line"), {"line": line_id}
            ).scalars()
        )
        bounds = conn.execute(
            text(
                "SELECT min(recorded_at), max(recorded_at) FROM process_step_results "
                "WHERE operation_id = ANY(:ops)"
            ),
            {"ops": ops},
        ).one()
        conn.execute(
            text("DELETE FROM process_characteristic_daily WHERE operation_id = ANY(:ops)"), {"ops": ops}
        )
        conn.execute(text("DELETE FROM process_step_daily WHERE operation_id = ANY(:ops)"), {"ops": ops})
    if bounds[0] is None:
        return {"step_rows": 0, "characteristic_rows": 0}

    months = _month_starts(bounds[0], bounds[1])
    for t0, t1 in zip(months, months[1:], strict=False):
        with engine.begin() as conn:
            _build_window(conn, ops, tz, t0, t1)

    with engine.begin() as conn:
        counts = {
            "step_rows": conn.execute(
                text("SELECT count(*) FROM process_step_daily WHERE operation_id = ANY(:ops)"), {"ops": ops}
            ).scalar_one(),
            "characteristic_rows": conn.execute(
                text("SELECT count(*) FROM process_characteristic_daily WHERE operation_id = ANY(:ops)"),
                {"ops": ops},
            ).scalar_one(),
        }
        specs = list(
            conn.execute(
                text(
                    "SELECT DISTINCT specification_id::text FROM process_characteristic_daily "
                    "WHERE operation_id = ANY(:ops) AND specification_id IS NOT NULL"
                ),
                {"ops": ops},
            ).scalars()
        )
        conn.execute(
            text(
                "INSERT INTO process_stats_builds (id, line_id, engine_name, engine_version, details) "
                "VALUES (:id, :line, :name, :version, CAST(:details AS jsonb))"
            ),
            {
                "id": uuid7(),
                "line": line_id,
                "name": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "details": json.dumps({"timezone": tz, "specification_ids": sorted(specs), **counts}),
            },
        )
    return counts


def _build_window(conn: Connection, ops: list[uuid.UUID], tz: str, t0: datetime, t1: datetime) -> None:
    params = {"ops": ops, "tz": tz, "t0": t0, "t1": t1}
    conn.execute(text(_INSERT_CHAR), params)
    conn.execute(text(_INSERT_STEP), params)
