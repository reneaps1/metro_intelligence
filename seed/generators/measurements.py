"""F3.3 (MI-18): ~90 days of measurement history per characteristic, with the
five scenario patterns from scenarios.yaml assigned across characteristics so
every downstream engine (F7-F10) has something real to react to: at least one
stable/capable, slow-drift, shift-after-event, high-variance, and NOK-outlier
characteristic. Out of scope here: process events (F3.4) — this generator
uses its own default event-day offset until F3.4 provides real timestamps to
sync against."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import insert

from app.models import (
    Characteristic,
    Connector,
    DataSource,
    Machine,
    MeasurementResult,
    MeasurementRun,
    MeasurementSample,
    PartNumber,
    Specification,
)

from seed.config.loader import Scenario
from seed.generators.base import SeedContext, register_generator

SCENARIO_CYCLE = ["stable_capable", "slow_drift", "shift_after_event", "high_variance", "outlier_nok"]
SAMPLES_PER_RUN = 6
ACTIVE_DAY_PROBABILITY = 0.75  # shift pattern: not every calendar day has a run
DRIFT_REFERENCE_DAY = 75  # the drift scenario should be visibly crossing the limit around here


def _active_spec(characteristic: Characteristic) -> Specification:
    for spec in characteristic.specifications:
        if spec.valid_to is None:
            return spec
    raise ValueError(f"No active specification for characteristic {characteristic.id}")


def _tolerance_limit(spec: Specification) -> float:
    """The tolerance magnitude scenarios scale noise/drift against: the upper
    bound if present (bilateral, or unilateral upper-only), else the
    magnitude of the lower bound."""
    if spec.upper_tol is not None:
        return float(spec.upper_tol)
    return abs(float(spec.lower_tol))


def _sample_deviation(rng, scenario: Scenario, spec: Specification, day_offset: int) -> float:
    limit = _tolerance_limit(spec)
    noise_std = limit * scenario.noise_std_fraction_of_tolerance

    if scenario.name == "slow_drift":
        progress = day_offset / DRIFT_REFERENCE_DAY
        center = progress * scenario.drift_fraction * limit
        return float(rng.normal(center, noise_std))

    if scenario.name == "shift_after_event":
        event_day = scenario.event_day_offset or 0
        center = scenario.shift_fraction * limit if day_offset >= event_day else 0.0
        return float(rng.normal(center, noise_std))

    if scenario.name == "outlier_nok":
        if rng.random() < scenario.nok_outlier_probability:
            sign = 1 if rng.random() < 0.5 else -1
            return float(limit * scenario.nok_outlier_magnitude_fraction * sign)
        return float(rng.normal(0.0, noise_std))

    # stable_capable and high_variance both center on nominal; only their
    # noise_std_fraction_of_tolerance (set in scenarios.yaml) differs.
    return float(rng.normal(0.0, noise_std))


@register_generator
def generate_measurement_series(context: SeedContext) -> None:
    session = context.session
    rng = context.rng
    settings = context.config.settings

    parts: list[PartNumber] = context.artifacts["parts"]
    characteristics: list[Characteristic] = context.artifacts["characteristics"]
    machines: list[Machine] = context.artifacts["machines"]

    chars_by_part: dict = {}
    for characteristic in characteristics:
        chars_by_part.setdefault(characteristic.part_number_id, []).append(characteristic)

    scenario_by_characteristic_id: dict = {}
    for part_characteristics in chars_by_part.values():
        for i, characteristic in enumerate(part_characteristics):
            scenario_by_characteristic_id[characteristic.id] = SCENARIO_CYCLE[i % len(SCENARIO_CYCLE)]

    connector = Connector(code="seed-manual-upload", name="Seed Manual Upload (Demo)", connector_type="manual_upload")
    data_source = DataSource(code="seed-cmm-line", name="Seed CMM/Scanner Line (Demo)", connector=connector)
    session.add_all([connector, data_source])

    now = datetime.now(timezone.utc)
    start_day = now - timedelta(days=settings.history_days)

    result_rows: list[dict] = []

    for part_index, part in enumerate(parts):
        machine = machines[part_index % len(machines)]
        part_characteristics = chars_by_part.get(part.id, [])
        program = part.measurement_programs[0]

        for day_offset in range(settings.history_days + 1):
            if rng.random() > ACTIVE_DAY_PROBABILITY:
                continue  # shift pattern: this day had no run

            run_date = start_day + timedelta(days=day_offset)
            run = MeasurementRun(
                part_number=part,
                measurement_program=program,
                data_source=data_source,
                machine=machine,
                started_at=run_date,
                batch_code=f"BATCH-{run_date:%Y%m%d}",
            )
            session.add(run)

            samples = [MeasurementSample(sample_index=i) for i in range(1, SAMPLES_PER_RUN + 1)]
            run.samples.extend(samples)
            session.flush()  # one flush per run populates every sample's id

            for sample in samples:
                measured_at = run_date + timedelta(minutes=sample.sample_index)
                for characteristic in part_characteristics:
                    scenario = context.config.scenario(scenario_by_characteristic_id[characteristic.id])
                    spec = _active_spec(characteristic)
                    deviation = _sample_deviation(rng, scenario, spec, day_offset)
                    value = float(spec.nominal) + deviation
                    is_ok = (spec.lower_tol is None or deviation >= float(spec.lower_tol)) and (
                        spec.upper_tol is None or deviation <= float(spec.upper_tol)
                    )
                    result_rows.append(
                        {
                            "measurement_sample_id": sample.id,
                            "characteristic_id": characteristic.id,
                            "specification_id": spec.id,
                            "value": round(value, 6),
                            "deviation": round(deviation, 6),
                            "is_ok": is_ok,
                            "measured_at": measured_at,
                        }
                    )

    # Bulk insert (tens of thousands of rows): a Core multi-row INSERT, not the
    # ORM's per-object unit-of-work, is what makes the ">50k rows in <2 min"
    # acceptance criterion achievable.
    if result_rows:
        session.execute(insert(MeasurementResult), result_rows)

    context.artifacts["scenario_by_characteristic_id"] = scenario_by_characteristic_id
    context.artifacts["measurement_result_count"] = len(result_rows)
