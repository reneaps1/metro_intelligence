"""Read side of the per-step process views (ADR-005).

KPIs come from the derived daily tables, so they stay fast over tens of
millions of results. Only the histogram and the piece trace read raw
results, both bounded by characteristic or piece and by date.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.engines.spc.capability import Moments, ToleranceSpec, cp_from_moments, cpk_from_moments
from app.models import Characteristic, Line, Operation, PartInstance, PartNumber, Recipe, Specification
from app.schemas.process import (
    BreakdownRow,
    CharacteristicDailyPoint,
    CharacteristicDetail,
    CharacteristicSummary,
    DailyCount,
    DateRange,
    HistogramBin,
    LineOverview,
    LineRead,
    OperationRead,
    OperationSummary,
    PieceTrace,
    RecipeRead,
    SpecLimits,
    StepOverview,
    TraceStep,
    TraceValue,
)
from app.services.process_status import step_status

DEFAULT_RANGE_DAYS = 30
NO_RECIPE_KEY = "none"


class NotFound(LookupError):
    """The requested line, operation, characteristic or piece does not exist."""


# --------------------------------------------------------------------- helpers
def _operation_read(op: Operation) -> OperationRead:
    return OperationRead(
        id=op.id, code=op.code, name=op.name, kind=op.operation_kind, side=op.side, sequence=op.sequence
    )


def _line_read(db: Session, line: Line) -> LineRead:
    ops = db.execute(
        select(Operation).where(Operation.line_id == line.id).order_by(Operation.sequence)
    ).scalars()
    return LineRead(
        id=line.id, code=line.code, name=line.name, operations=[_operation_read(op) for op in ops]
    )


def _rate(part: int, whole: int) -> float | None:
    return part / whole if whole else None


def _spec_limits(spec: Specification | None) -> SpecLimits | None:
    if spec is None:
        return None
    return SpecLimits(
        nominal=spec.nominal,
        lower_tol=spec.lower_tol,
        upper_tol=spec.upper_tol,
        lower_limit=None if spec.lower_tol is None else spec.nominal + spec.lower_tol,
        upper_limit=None if spec.upper_tol is None else spec.nominal + spec.upper_tol,
    )


def _capability(
    n: int, total: float, total_sq: float, spec: Specification | None
) -> tuple[float | None, float | None, str | None]:
    """(Cp, Cpk/Cpu/Cpl, kind) from moments against `spec`; None when undefined."""
    if spec is None or n < 2:
        return None, None, None
    tolerance = ToleranceSpec(nominal=spec.nominal, lower_tol=spec.lower_tol, upper_tol=spec.upper_tol)
    moments = Moments(n, Decimal(repr(total)), Decimal(repr(total_sq)))
    kind = (
        "Cpk"
        if spec.lower_tol is not None and spec.upper_tol is not None
        else ("Cpu" if spec.upper_tol is not None else "Cpl")
    )
    try:
        cpk = float(cpk_from_moments(moments, tolerance))
    except ValueError:
        return None, None, kind
    cp_value = None
    if kind == "Cpk":
        try:
            cp_value = float(cp_from_moments(moments, tolerance))
        except ValueError:
            cp_value = None
    return cp_value, cpk, kind


def _active_specs(db: Session, characteristic_ids: list[uuid.UUID]) -> dict[uuid.UUID, Specification]:
    if not characteristic_ids:
        return {}
    specs = db.execute(
        select(Specification).where(
            Specification.characteristic_id.in_(characteristic_ids), Specification.valid_to.is_(None)
        )
    ).scalars()
    return {spec.characteristic_id: spec for spec in specs}


@dataclass(frozen=True)
class Filters:
    start: date
    end: date
    recipe_ids: list[uuid.UUID]

    def sql(self, alias: str = "d") -> str:
        recipe = "" if not self.recipe_ids else f" AND {alias}.recipe_id = ANY(:recipe_ids)"
        return f"{alias}.day >= :start AND {alias}.day <= :end{recipe}"

    def params(self) -> dict[str, Any]:
        return {"start": self.start, "end": self.end, "recipe_ids": self.recipe_ids}


def _available_days(db: Session, operation_ids: list[uuid.UUID]) -> tuple[date | None, date | None]:
    row = db.execute(
        text("SELECT min(day), max(day) FROM process_step_daily WHERE operation_id = ANY(:ops)"),
        {"ops": operation_ids},
    ).one()
    return row[0], row[1]


def resolve_range(
    db: Session, operation_ids: list[uuid.UUID], start: date | None, end: date | None
) -> DateRange:
    """Default: the last 30 days that have data."""
    first, last = _available_days(db, operation_ids)
    end = end or last or date.today()
    start = start or (end - timedelta(days=DEFAULT_RANGE_DAYS - 1))
    if start > end:
        start, end = end, start
    return DateRange(start=start, end=end, first_available=first, last_available=last)


def recipe_reads(db: Session, line_id: uuid.UUID) -> list[RecipeRead]:
    rows = db.execute(
        select(Recipe, PartNumber.code)
        .outerjoin(PartNumber, PartNumber.id == Recipe.variant_part_number_id)
        .where(Recipe.line_id == line_id)
        .order_by(Recipe.code)
    ).all()
    return [_recipe_read(recipe, variant_code) for recipe, variant_code in rows]


def _recipe_read(recipe: Recipe, variant_code: str | None) -> RecipeRead:
    pending = recipe.variant_label is None
    label = recipe.variant_label or f"Recipe {recipe.code} (variant pending)"
    return RecipeRead(
        id=recipe.id, code=recipe.code, label=label, variant_part_number=variant_code, variant_pending=pending
    )


# ------------------------------------------------------------------- endpoints
def list_lines(db: Session) -> list[LineRead]:
    lines = db.execute(
        select(Line).where(Line.id.in_(select(Operation.line_id))).order_by(Line.code)
    ).scalars()
    return [_line_read(db, line) for line in lines]


def _characteristic_moments(db: Session, filters: Filters, operation_ids: list[uuid.UUID]) -> list[Any]:
    return list(
        db.execute(
            text(
                f"""
                SELECT d.operation_id, d.characteristic_id, sum(d.n) AS n,
                       sum(d.n_machine_nok) AS machine_nok,
                       sum(d.n_evaluated) AS evaluated, sum(d.n_spec_nok) AS spec_nok,
                       sum(d.n_machine_ok_spec_nok) AS disagreements, sum(d.sum_value) AS total,
                       sum(d.sum_sq_value) AS total_sq, min(d.min_value) AS min_value,
                       max(d.max_value) AS max_value
                FROM process_characteristic_daily d
                WHERE d.operation_id = ANY(:ops) AND {filters.sql()}
                GROUP BY d.operation_id, d.characteristic_id
                """
            ),
            {"ops": operation_ids, **filters.params()},
        )
    )


def line_overview(
    db: Session, line_id: uuid.UUID, start: date | None, end: date | None, recipe_ids: list[uuid.UUID]
) -> LineOverview:
    line = db.get(Line, line_id)
    if line is None:
        raise NotFound("Line not found.")
    line_read = _line_read(db, line)
    op_ids = [op.id for op in line_read.operations]
    date_range = resolve_range(db, op_ids, start, end)
    filters = Filters(date_range.start, date_range.end, recipe_ids)

    totals = {
        row.operation_id: row
        for row in db.execute(
            text(
                f"""
                SELECT d.operation_id, sum(d.pieces) AS pieces, sum(d.pieces_machine_nok) AS machine_nok,
                       sum(d.pieces_spec_nok) AS spec_nok, sum(d.first_attempt_ok) AS first_ok,
                       sum(d.repeat_attempts) AS repeats
                FROM process_step_daily d
                WHERE d.operation_id = ANY(:ops) AND {filters.sql()}
                GROUP BY d.operation_id
                """
            ),
            {"ops": op_ids, **filters.params()},
        )
    }
    trends: dict[uuid.UUID, list[DailyCount]] = defaultdict(list)
    for row in db.execute(
        text(
            f"""
            SELECT d.operation_id, d.day, sum(d.pieces) AS pieces, sum(d.pieces_machine_nok) AS machine_nok,
                   sum(d.pieces_spec_nok) AS spec_nok
            FROM process_step_daily d
            WHERE d.operation_id = ANY(:ops) AND {filters.sql()}
            GROUP BY d.operation_id, d.day ORDER BY d.day
            """
        ),
        {"ops": op_ids, **filters.params()},
    ):
        trends[row.operation_id].append(
            DailyCount(
                day=row.day,
                pieces=int(row.pieces),
                machine_nok=int(row.machine_nok),
                spec_nok=int(row.spec_nok),
            )
        )

    moments = _characteristic_moments(db, filters, op_ids)
    specs = _active_specs(db, list({row.characteristic_id for row in moments}))
    worst_cpk: dict[uuid.UUID, float] = {}
    has_spec: dict[uuid.UUID, bool] = defaultdict(bool)
    disagreements: dict[uuid.UUID, int] = defaultdict(int)
    for row in moments:
        disagreements[row.operation_id] += int(row.disagreements)
        if row.evaluated:
            has_spec[row.operation_id] = True
        _cp, cpk, _kind = _capability(int(row.n), row.total, row.total_sq, specs.get(row.characteristic_id))
        if cpk is not None:
            worst_cpk[row.operation_id] = min(cpk, worst_cpk.get(row.operation_id, cpk))

    type_check = next((op for op in line_read.operations if op.kind == "type_check"), None)
    reference = int(totals[type_check.id].pieces) if type_check and type_check.id in totals else 0

    steps = []
    for op in line_read.operations:
        step_row = totals.get(op.id)
        pieces = int(step_row.pieces) if step_row else 0
        machine_nok = int(step_row.machine_nok) if step_row else 0
        spec_nok = int(step_row.spec_nok) if step_row else 0
        spec_rate = _rate(spec_nok, pieces) if has_spec[op.id] else None
        machine_rate = _rate(machine_nok, pieces)
        steps.append(
            StepOverview(
                operation=op,
                pieces=pieces,
                machine_nok=machine_nok,
                machine_nok_rate=machine_rate,
                spec_nok=spec_nok,
                spec_nok_rate=spec_rate,
                first_pass_yield=_rate(int(step_row.first_ok), pieces) if step_row else None,
                repeat_attempts=int(step_row.repeats) if step_row else 0,
                has_specification=has_spec[op.id],
                worst_cpk=worst_cpk.get(op.id),
                disagreements=disagreements[op.id],
                coverage=_rate(pieces, reference),
                status=step_status(
                    pieces, spec_rate if has_spec[op.id] else machine_rate, worst_cpk.get(op.id)
                ),
                trend=trends.get(op.id, []),
            )
        )
    return LineOverview(
        line=line_read,
        range=date_range,
        recipes=recipe_reads(db, line_id),
        selected_recipe_ids=recipe_ids,
        reference_pieces=reference,
        steps=steps,
    )


def _summaries(
    db: Session, rows: list[Any], specs: dict[uuid.UUID, Specification]
) -> list[CharacteristicSummary]:
    characteristics = {
        c.id: c
        for c in db.execute(
            select(Characteristic).where(Characteristic.id.in_([row.characteristic_id for row in rows]))
        ).scalars()
    }
    summaries = []
    for row in rows:
        char = characteristics[row.characteristic_id]
        n = int(row.n)
        mean = row.total / n if n else None
        variance = (row.total_sq - row.total * row.total / n) / (n - 1) if n > 1 else None
        spec = specs.get(char.id)
        cp_value, cpk, kind = _capability(n, row.total, row.total_sq, spec)
        summaries.append(
            CharacteristicSummary(
                id=char.id,
                code=char.balloon_number,
                name=char.name.split(" · ", 1)[-1],
                unit=char.unit,
                n=n,
                mean=mean,
                std_dev=max(variance, 0.0) ** 0.5 if variance is not None else None,
                min=row.min_value,
                max=row.max_value,
                machine_nok=int(row.machine_nok),
                spec_nok=int(row.spec_nok),
                machine_ok_spec_nok=int(row.disagreements),
                specification=_spec_limits(spec),
                cp=cp_value,
                cpk=cpk,
                capability_kind=kind,  # type: ignore[arg-type]
            )
        )
    return sorted(summaries, key=lambda s: _measure_order(s.code))


def _measure_order(code: str) -> tuple[int, int, str]:
    """REF first, then pins in numeric order, X before Y; electrical by points."""
    measure = code.split("-")[-1] if "-P" in code or code.endswith("-REF") else code
    if measure == "REF":
        return (0, 0, "")
    if measure.startswith("P") and measure[1:].rstrip("XY").isdigit():
        return (1, int(measure[1:].rstrip("XY")), measure[-1])
    return (2, 0, code)


def operation_summary(
    db: Session, operation_id: uuid.UUID, start: date | None, end: date | None, recipe_ids: list[uuid.UUID]
) -> OperationSummary:
    op = db.get(Operation, operation_id)
    if op is None:
        raise NotFound("Operation not found.")
    date_range = resolve_range(db, [op.id], start, end)
    filters = Filters(date_range.start, date_range.end, recipe_ids)
    params = {"op": op.id, **filters.params()}

    total = db.execute(
        text(
            f"""
            SELECT coalesce(sum(d.pieces), 0) AS pieces,
                   coalesce(sum(d.pieces_machine_nok), 0) AS machine_nok,
                   coalesce(sum(d.pieces_spec_nok), 0) AS spec_nok,
                   coalesce(sum(d.repeat_attempts), 0) AS repeats
            FROM process_step_daily d WHERE d.operation_id = :op AND {filters.sql()}
            """
        ),
        params,
    ).one()
    rows = _characteristic_moments(db, filters, [op.id])
    specs = _active_specs(db, [row.characteristic_id for row in rows])
    characteristics = _summaries(db, rows, specs)

    recipes = {r.id: r for r in recipe_reads(db, op.line_id)}
    by_recipe = [
        BreakdownRow(
            key=str(row.recipe_id) if row.recipe_id else NO_RECIPE_KEY,
            label=recipes[row.recipe_id].label
            if row.recipe_id in recipes
            else "No recipe (not seen at type check)",
            pieces=int(row.pieces),
            machine_nok=int(row.machine_nok),
            spec_nok=int(row.spec_nok),
        )
        for row in db.execute(
            text(
                f"""
                SELECT d.recipe_id, sum(d.pieces) AS pieces, sum(d.pieces_machine_nok) AS machine_nok,
                       sum(d.pieces_spec_nok) AS spec_nok
                FROM process_step_daily d WHERE d.operation_id = :op AND {filters.sql()}
                GROUP BY d.recipe_id ORDER BY sum(d.pieces) DESC
                """
            ),
            params,
        )
    ]
    by_nest = [
        BreakdownRow(
            key=str(row.nest) if row.nest is not None else NO_RECIPE_KEY,
            label=f"Nest {row.nest}" if row.nest is not None else "No nest",
            pieces=int(row.pieces),
            machine_nok=int(row.machine_nok),
            spec_nok=int(row.spec_nok),
        )
        for row in db.execute(
            text(
                f"""
                SELECT d.nest, sum(d.pieces) AS pieces, sum(d.pieces_machine_nok) AS machine_nok,
                       sum(d.pieces_spec_nok) AS spec_nok
                FROM process_step_daily d WHERE d.operation_id = :op AND {filters.sql()}
                GROUP BY d.nest ORDER BY d.nest NULLS LAST
                """
            ),
            params,
        )
    ]
    trend = [
        DailyCount(
            day=row.day, pieces=int(row.pieces), machine_nok=int(row.machine_nok), spec_nok=int(row.spec_nok)
        )
        for row in db.execute(
            text(
                f"""
                SELECT d.day, sum(d.pieces) AS pieces, sum(d.pieces_machine_nok) AS machine_nok,
                       sum(d.pieces_spec_nok) AS spec_nok
                FROM process_step_daily d WHERE d.operation_id = :op AND {filters.sql()}
                GROUP BY d.day ORDER BY d.day
                """
            ),
            params,
        )
    ]
    has_spec = any(c.specification is not None for c in characteristics)
    cpks = [c.cpk for c in characteristics if c.cpk is not None]
    pieces = int(total.pieces)
    nok = int(total.spec_nok) if has_spec else int(total.machine_nok)
    return OperationSummary(
        operation=_operation_read(op),
        range=date_range,
        pieces=pieces,
        machine_nok=int(total.machine_nok),
        spec_nok=int(total.spec_nok),
        repeat_attempts=int(total.repeats),
        disagreements=sum(c.machine_ok_spec_nok for c in characteristics),
        status=step_status(pieces, _rate(nok, pieces), min(cpks) if cpks else None),
        characteristics=characteristics,
        by_recipe=by_recipe,
        by_nest=by_nest,
        trend=trend,
    )


def characteristic_detail(
    db: Session,
    operation_id: uuid.UUID,
    characteristic_id: uuid.UUID,
    start: date | None,
    end: date | None,
    recipe_ids: list[uuid.UUID],
    bins: int,
) -> CharacteristicDetail:
    op = db.get(Operation, operation_id)
    if op is None or db.get(Characteristic, characteristic_id) is None:
        raise NotFound("Characteristic not found.")
    date_range = resolve_range(db, [op.id], start, end)
    filters = Filters(date_range.start, date_range.end, recipe_ids)
    rows = [
        row
        for row in _characteristic_moments(db, filters, [op.id])
        if row.characteristic_id == characteristic_id
    ]
    if not rows:
        raise NotFound("No values for this characteristic in the selected range.")
    spec = _active_specs(db, [characteristic_id]).get(characteristic_id)
    summary = _summaries(db, rows, {characteristic_id: spec} if spec else {})[0]

    daily = []
    for row in db.execute(
        text(
            f"""
            SELECT d.day, sum(d.n) AS n, sum(d.sum_value) AS total, sum(d.sum_sq_value) AS total_sq,
                   min(d.min_value) AS min_value, max(d.max_value) AS max_value,
                   sum(d.n_spec_nok) AS spec_nok, sum(d.n_machine_nok) AS machine_nok
            FROM process_characteristic_daily d
            WHERE d.operation_id = :op AND d.characteristic_id = :cid AND {filters.sql()}
            GROUP BY d.day ORDER BY d.day
            """
        ),
        {"op": op.id, "cid": characteristic_id, **filters.params()},
    ):
        n = int(row.n)
        _cp, cpk, _kind = _capability(n, row.total, row.total_sq, spec)
        daily.append(
            CharacteristicDailyPoint(
                day=row.day,
                n=n,
                mean=row.total / n,
                min=row.min_value,
                max=row.max_value,
                spec_nok=int(row.spec_nok),
                machine_nok=int(row.machine_nok),
                cpk=cpk,
            )
        )

    bins_out, below, above = _histogram(db, op, characteristic_id, filters, spec, bins)
    return CharacteristicDetail(
        characteristic=summary,
        range=date_range,
        bins=bins_out,
        below_range=below,
        above_range=above,
        daily=daily,
    )


def _histogram(
    db: Session,
    op: Operation,
    characteristic_id: uuid.UUID,
    filters: Filters,
    spec: Specification | None,
    bins: int,
) -> tuple[list[HistogramBin], int, int]:
    """Histogram of raw values, partition-pruned by date. The range is the
    0.5th-99.5th percentile widened to the specification limits, so a few
    gross outliers do not flatten the distribution."""
    tz = (
        db.execute(
            text(
                "SELECT s.timezone FROM org_sites s JOIN org_areas a ON a.site_id = s.id "
                "JOIN org_lines l ON l.area_id = a.id WHERE l.id = :line"
            ),
            {"line": op.line_id},
        ).scalar_one_or_none()
        or "UTC"
    )
    recipe = "" if not filters.recipe_ids else " AND pi.recipe_id = ANY(:recipe_ids)"
    source = f"""
        FROM measurement_results r
        JOIN process_step_results sr ON sr.measurement_sample_id = r.measurement_sample_id
        JOIN process_part_instances pi ON pi.id = sr.part_instance_id
        WHERE r.characteristic_id = :cid AND sr.operation_id = :op
          AND r.measured_at >= (CAST(:start AS date)::timestamp AT TIME ZONE :tz)
          AND r.measured_at < ((CAST(:end AS date) + 1)::timestamp AT TIME ZONE :tz){recipe}
    """
    params = {"cid": characteristic_id, "op": op.id, "tz": tz, **filters.params()}
    low, high = db.execute(
        text(
            "SELECT percentile_cont(0.005) WITHIN GROUP (ORDER BY r.value::float8), "
            f"percentile_cont(0.995) WITHIN GROUP (ORDER BY r.value::float8) {source}"
        ),
        params,
    ).one()
    if low is None:
        return [], 0, 0
    limits = _spec_limits(spec)
    if limits is not None:
        if limits.lower_limit is not None:
            low = min(low, float(limits.lower_limit))
        if limits.upper_limit is not None:
            high = max(high, float(limits.upper_limit))
    if high <= low:
        high = low + 1e-6
    counts: dict[int, int] = dict(
        db.execute(  # type: ignore[arg-type]
            text(
                f"SELECT width_bucket(r.value::float8, :low, :high, :bins) AS b, count(*) {source} GROUP BY 1"
            ),
            {**params, "low": low, "high": high, "bins": bins},
        ).all()
    )
    width = (high - low) / bins
    out = [
        HistogramBin(lower=low + i * width, upper=low + (i + 1) * width, count=int(counts.get(i + 1, 0)))
        for i in range(bins)
    ]
    # width_bucket puts the exact upper bound in bin n+1; count it in the last bin.
    return out, int(counts.get(0, 0)), int(counts.get(bins + 1, 0))


def piece_trace(db: Session, serial_number: str) -> PieceTrace:
    instance = db.execute(
        select(PartInstance).where(PartInstance.serial_number == serial_number).limit(1)
    ).scalar_one_or_none()
    if instance is None:
        raise NotFound("Piece not found.")
    line = db.get(Line, instance.line_id)
    assert line is not None
    recipe_read = None
    if instance.recipe_id is not None:
        recipe = db.get(Recipe, instance.recipe_id)
        assert recipe is not None
        variant = db.get(PartNumber, recipe.variant_part_number_id) if recipe.variant_part_number_id else None
        recipe_read = _recipe_read(recipe, variant.code if variant else None)

    steps_rows = db.execute(
        text(
            """
            SELECT sr.*, o.sequence FROM process_step_results sr
            JOIN process_operations o ON o.id = sr.operation_id
            WHERE sr.part_instance_id = :pid ORDER BY o.sequence, sr.attempt_no
            """
        ),
        {"pid": instance.id},
    ).all()
    sample_ids = [row.measurement_sample_id for row in steps_rows]
    times = sorted({row.recorded_at for row in steps_rows})
    values_by_sample: dict[uuid.UUID, list[TraceValue]] = defaultdict(list)
    if sample_ids:
        results = db.execute(
            text(
                """
                SELECT r.measurement_sample_id, r.characteristic_id, r.value, r.machine_ok, r.is_ok,
                       r.deviation, r.specification_id, c.balloon_number, c.name, c.unit
                FROM measurement_results r JOIN catalog_characteristics c ON c.id = r.characteristic_id
                WHERE r.measurement_sample_id = ANY(:samples) AND r.measured_at = ANY(:times)
                """
            ),
            {"samples": sample_ids, "times": times},
        ).all()
        spec_ids = {row.specification_id for row in results if row.specification_id}
        specs = {
            s.id: s for s in db.execute(select(Specification).where(Specification.id.in_(spec_ids))).scalars()
        }
        for row in results:
            values_by_sample[row.measurement_sample_id].append(
                TraceValue(
                    characteristic_id=row.characteristic_id,
                    code=row.balloon_number,
                    name=row.name.split(" · ", 1)[-1],
                    unit=row.unit,
                    value=row.value,
                    machine_ok=row.machine_ok,
                    is_ok=row.is_ok,
                    deviation=row.deviation,
                    specification=_spec_limits(specs.get(row.specification_id)),
                )
            )
    operations = {op.id: op for op in _line_read(db, line).operations}
    steps = [
        TraceStep(
            operation=operations[row.operation_id],
            attempt=row.attempt_no,
            recorded_at=row.recorded_at,
            nest=row.nest,
            program_number=row.program_number,
            machine_ok=row.machine_ok,
            values=sorted(
                values_by_sample.get(row.measurement_sample_id, []), key=lambda v: _measure_order(v.code)
            ),
        )
        for row in steps_rows
    ]
    return PieceTrace(
        serial_number=instance.serial_number,
        line=_line_read(db, line),
        recipe=recipe_read,
        first_seen_at=instance.first_seen_at,
        steps=steps,
    )
