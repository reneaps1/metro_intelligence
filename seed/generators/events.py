"""F3.4 (MI-19): process events synced with F3.3's shift_after_event
characteristics. Every part that has one gets a correlated `tool_change`
event within ±2h of the real jump day (scenarios.yaml's shift_after_event
event_day_offset, applied to the exact start_day F3.3 used — see
context.artifacts["history_start_day"]), so the Risk Engine's future
event-correlation logic has something true to find. The remaining events are
spread across the 90-day history window for narrative variety (maintenance,
lot changes, adjustments) without pretending to correlate with anything."""
from __future__ import annotations

from datetime import timedelta

from app.models import Characteristic, Machine, PartNumber, ProcessEvent

from seed.generators.base import SeedContext, register_generator

TARGET_EVENT_COUNT = 20
EVENT_JITTER_MINUTES = 2 * 60  # ±2h acceptance criterion

OTHER_EVENT_TYPES = ["maintenance", "material_lot_change", "machine_adjustment"]

EVENT_DESCRIPTIONS = {
    "tool_change": "Cambio de herramienta programado (demo).",
    "maintenance": "Mantenimiento preventivo de máquina (demo).",
    "material_lot_change": "Cambio de lote de material (demo).",
    "machine_adjustment": "Ajuste de parámetros de máquina (demo).",
}


@register_generator
def generate_process_events(context: SeedContext) -> None:
    session = context.session
    rng = context.rng

    parts: list[PartNumber] = context.artifacts["parts"]
    machines: list[Machine] = context.artifacts["machines"]
    characteristics: list[Characteristic] = context.artifacts["characteristics"]
    scenario_by_characteristic_id: dict = context.artifacts["scenario_by_characteristic_id"]
    start_day = context.artifacts["history_start_day"]
    shift_event_day = context.config.scenario("shift_after_event").event_day_offset or 0

    parts_with_shift: set = {
        characteristic.part_number_id
        for characteristic in characteristics
        if scenario_by_characteristic_id.get(characteristic.id) == "shift_after_event"
    }

    events: list[ProcessEvent] = []

    # Correlated events: one per part with a shift_after_event characteristic,
    # on the same machine F3.3 assigned that part (part_index % len(machines),
    # mirroring generate_measurement_series), jittered ±2h around the real
    # jump day.
    for part_index, part in enumerate(parts):
        if part.id not in parts_with_shift:
            continue
        machine = machines[part_index % len(machines)]
        jitter_minutes = int(rng.integers(-EVENT_JITTER_MINUTES, EVENT_JITTER_MINUTES + 1))
        occurred_at = start_day + timedelta(days=shift_event_day, minutes=jitter_minutes)
        events.append(
            ProcessEvent(
                event_type="tool_change",
                line_id=machine.cell.line_id,
                machine_id=machine.id,
                occurred_at=occurred_at,
                description=f"{EVENT_DESCRIPTIONS['tool_change']} ({part.code})",
                event_metadata={"part_code": part.code, "correlated_scenario": "shift_after_event"},
            )
        )

    # Fill the rest of the ~20-event narrative with uncorrelated events spread
    # across the full 90-day window.
    remaining = max(0, TARGET_EVENT_COUNT - len(events))
    for _ in range(remaining):
        machine = machines[int(rng.integers(0, len(machines)))]
        event_type = OTHER_EVENT_TYPES[int(rng.integers(0, len(OTHER_EVENT_TYPES)))]
        day_offset = int(rng.integers(0, 91))
        minute_offset = int(rng.integers(0, 24 * 60))
        occurred_at = start_day + timedelta(days=day_offset, minutes=minute_offset)
        events.append(
            ProcessEvent(
                event_type=event_type,
                line_id=machine.cell.line_id,
                machine_id=machine.id,
                occurred_at=occurred_at,
                description=EVENT_DESCRIPTIONS[event_type],
                event_metadata={},
            )
        )

    session.add_all(events)
    session.flush()
    context.artifacts["process_events"] = events
