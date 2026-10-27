"""Synthetic, client-shaped dimensional dataset for the demo (IQ-F5).

SIMULATED: invented variables, tolerances and defects. It mimics the *shape*
of an injection-moulding inspection dataset (shots x nests x dimensions) and
carries known, documented mechanisms so every chart has something real to
find -- and the presenter can say exactly what was injected.

Deterministic: fixed seed, built once and cached.
"""

from __future__ import annotations

import os
import random
from datetime import UTC, datetime
from functools import lru_cache

from app.engines.quality_analytics.dataset import DimensionalDataset, Variable

SYNTHETIC_DATASET_ID = "demo-synthetic-dimensional"
GENERATOR_VERSION = "dim-sim-1.0.0"
SEED = 20261013

PERIOD_START = datetime(2026, 10, 13, 0, 0, tzinfo=UTC)
DAYS = 7
GROUP_INTERVAL_S = 240.0  # one inspected shot every 4 min per machine
MACHINES = ("INY-01", "INY-02")
NEST_COUNT = 12
DEFAULT_CRITICAL_NEST = 4
H = 3600.0
D = 24 * H

VARIABLES: tuple[Variable, ...] = (
    Variable("PinsLength", "Longitud de pines", "mm", 12.000, -0.050, 0.050),
    Variable("PinPositionX", "Posición de pin X", "mm", 3.200, -0.040, 0.040),
    Variable("PinPositionY", "Posición de pin Y", "mm", 5.600, -0.040, 0.040),
    Variable("Coplanarity", "Coplanaridad", "mm", 0.000, None, 0.080),
    Variable("HousingWidth", "Ancho de carcasa", "mm", 18.500, -0.100, 0.100),
    Variable("HousingHeight", "Altura de carcasa", "mm", 7.250, -0.080, 0.080),
    Variable("SlotWidth", "Ancho de ranura", "mm", 1.200, -0.030, 0.030),
    Variable("HoleDiameter", "Diámetro de barreno", "mm", 2.500, -0.025, 0.025),
    Variable("Thickness", "Espesor de pared", "mm", 1.500, -0.050, 0.050),
    Variable("Flatness", "Planitud", "mm", 0.000, None, 0.060),
)

# Unilateral (form) characteristics are positive by nature: |N(mean, sd)|.
_FORM = {"Coplanarity": (0.025, 0.012), "Flatness": (0.018, 0.009)}

# NOK "waves": a temporary PinPositionY shift on one machine (offset_s, duration_s, machine).
WAVES = (
    (1.4 * D, 3 * H, "INY-01"),
    (2.6 * D, 2 * H, "INY-02"),
    (4.3 * D, 4 * H, "INY-01"),
    (5.8 * D, 2.5 * H, "INY-01"),
)
TOOL_CHANGE_S = 3.5 * D  # INY-01 HousingWidth wear drift resets here
WEAR_MM = 0.045
BATCH_PERIOD_S = 36 * H
BATCHES = ("MAT-A", "MAT-B", "MAT-C", "MAT-D", "MAT-E")
SHRINK_BATCH = "MAT-C"


def critical_nest() -> int:
    """Nest carrying the injected concentration of defects (configurable per deployment)."""
    try:
        value = int(os.getenv("DEMO_CRITICAL_NEST", DEFAULT_CRITICAL_NEST))
    except ValueError:
        return DEFAULT_CRITICAL_NEST
    return value if 1 <= value <= NEST_COUNT else DEFAULT_CRITICAL_NEST


def shift_of(epoch_s: float) -> str:
    hour = datetime.fromtimestamp(epoch_s, tz=UTC).hour
    if 6 <= hour < 14:
        return "A"
    if 14 <= hour < 22:
        return "B"
    return "C"


def _in_wave(offset: float, machine: str) -> bool:
    return any(start <= offset < start + dur and m == machine for start, dur, m in WAVES)


@lru_cache(maxsize=4)
def _build(crit: int) -> DimensionalDataset:
    rng = random.Random(SEED)
    nest_bias = {
        (m, n, v.key): rng.gauss(0.0, (v.upper_tol or 0.05) / 25)
        for m in MACHINES
        for n in range(1, NEST_COUNT + 1)
        for v in VARIABLES
    }
    base_sd = {v.key: (v.upper_tol or 0.05) / 3.9 for v in VARIABLES}

    timestamps: list[float] = []
    group_ids: list[int] = []
    machines: list[str | None] = []
    cavities: list[int | None] = []
    shifts: list[str | None] = []
    batches: list[str | None] = []
    values: dict[str, list[float | None]] = {v.key: [] for v in VARIABLES}

    start = PERIOD_START.timestamp()
    group = 0
    steps = int(DAYS * D / GROUP_INTERVAL_S)
    for step in range(steps):
        for mi, machine in enumerate(MACHINES):
            offset = step * GROUP_INTERVAL_S + mi * GROUP_INTERVAL_S / 2
            ts = start + offset
            shift = shift_of(ts)
            batch = BATCHES[min(int(offset // BATCH_PERIOD_S), len(BATCHES) - 1)]
            wave = _in_wave(offset, machine)
            wear = WEAR_MM * offset / TOOL_CHANGE_S if machine == "INY-01" and offset < TOOL_CHANGE_S else 0.0
            group += 1
            for nest in range(1, NEST_COUNT + 1):
                timestamps.append(ts)
                group_ids.append(group)
                machines.append(machine)
                cavities.append(nest)
                shifts.append(shift)
                batches.append(batch)
                for v in VARIABLES:
                    key = v.key
                    if key in _FORM:
                        mean, sd = _FORM[key]
                        if key == "Coplanarity" and machine == "INY-02":
                            mean += 0.010
                        values[key].append(round(abs(rng.gauss(mean, sd)), 4))
                        continue
                    mean = v.nominal + nest_bias[(machine, nest, key)]
                    sd = base_sd[key]
                    if nest == crit and key == "PinsLength":
                        mean += 0.028
                        sd *= 1.3
                    if nest == crit and key == "PinPositionX":
                        mean += 0.010
                    if wave and key == "PinPositionY":
                        mean += 0.030
                    if key == "HousingWidth":
                        mean += wear
                    if key == "Thickness" and shift == "C":
                        sd *= 1.3
                    if key == "SlotWidth" and batch == SHRINK_BATCH:
                        mean -= 0.009
                    values[key].append(round(rng.gauss(mean, sd), 4))

    wave_text = ", ".join(f"día {s / D:.1f} {m} ({d / H:.1f} h)" for s, d, m in WAVES)
    return DimensionalDataset(
        id=SYNTHETIC_DATASET_ID,
        name="Dataset dimensional sintético (estilo cliente)",
        description=(
            f"{DAYS} días, {len(MACHINES)} máquinas, {NEST_COUNT} nidos, {len(VARIABLES)} cotas. "
            "Generado con semilla fija: no son mediciones de ninguna planta."
        ),
        source_type="SIMULATED",
        variables=VARIABLES,
        timestamps=timestamps,
        group_ids=group_ids,
        machines=machines,
        cavities=cavities,
        shifts=shifts,
        batches=batches,
        values=values,
        mechanisms=[
            f"Nido {crit}: longitud de pines desplazada +0.028 mm y 30 % más dispersa; posición X +0.010 mm.",
            f"Oleadas NOK (posición Y +0.030 mm temporal): {wave_text}.",
            f"INY-01: desgaste de herramienta (ancho de carcasa hasta +{WEAR_MM} mm) "
            "hasta el cambio de herramienta en el día 3.5.",
            "Turno C (22–06 h): espesor de pared 30 % más disperso.",
            f"Lote {SHRINK_BATCH}: ancho de ranura −0.009 mm (contracción).",
            "INY-02: coplanaridad media +0.010 mm.",
        ],
    )


def synthetic_dataset() -> DimensionalDataset:
    return _build(critical_nest())
