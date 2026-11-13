"""IQ-F6: generates the fictitious dimensional CSVs used to demo the column
mapping import (seed/sample_files/mi_demo_dimensional_*.csv).

Both files are SIMULATED and deliberately shaped *unlike* the demo dataset
and unlike each other, so the import has something to map and the
analytics visibly change after loading them:

- ``mi_demo_dimensional_long.csv`` -- long layout (one row per measurement),
  ``;`` delimiter, decimal comma, separate date and time columns (D/M/Y),
  limits per row and a source OK/NOK column. 16 nests; nest 11 carries a
  pin-diameter offset and press PRS-B drifts on terminal length after day 2.
  The source verdict uses a tighter in-house flatness limit than the drawing
  limits in the file, so "reported by source" and "recalculated by spec"
  disagree on purpose. A handful of rows are broken on purpose (bad value,
  empty value, bad date, duplicate, wrong unit) to exercise quarantine.
- ``mi_demo_dimensional_wide.csv`` -- wide layout (one row per piece),
  ``,`` delimiter, ISO 8601 timestamps with offset, 8 cavities as
  ``CAV-0n``, no limits in the file (type them in the mapping screen, see
  seed/sample_files/README.md) and a PASS/FAIL column.

Deterministic: fixed seed, fixed dates. Run:
``python -m seed.scripts.generate_dimensional_samples``.
"""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "sample_files"
SEED = 20261027

# name, unit, nominal, lsl, usl, sd
LONG_VARIABLES = (
    ("Altura_Clip", "mm", 4.200, 4.150, 4.250, 0.012),
    ("Diametro_Pin", "mm", 0.640, 0.625, 0.655, 0.0035),
    ("Distancia_A", "mm", 10.500, 10.420, 10.580, 0.018),
    ("Planitud", "mm", 0.000, None, 0.050, None),
    ("Ancho_Ranura", "mm", 1.800, 1.770, 1.830, 0.007),
    ("Longitud_Terminal", "mm", 15.000, 14.940, 15.060, 0.013),
)
IN_HOUSE_FLATNESS_LIMIT = 0.040
LONG_NESTS = 16
LONG_CYCLES = 60
LONG_START = datetime(2026, 9, 1, 6, 0)
CRITICAL_NEST = 11

WIDE_VARIABLES = (
    # name, nominal, sd (limits are typed in the mapping screen)
    ("PinHeight", 2.500, 0.010),
    ("PinPitch", 1.270, 0.004),
    ("BodyLength", 22.000, 0.020),
    ("WallThickness", 0.800, 0.012),
    ("Warp", 0.000, None),
)
WIDE_CAVITIES = 8
WIDE_CYCLES = 150
WIDE_START = datetime(2026, 9, 15, 7, 0, tzinfo=timezone(timedelta(hours=-6)))


def _fmt(value: float, decimals: int = 4) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def _shift(dt: datetime) -> str:
    return "A" if 6 <= dt.hour < 14 else "B" if 14 <= dt.hour < 22 else "C"


def _long_rows(rng: random.Random) -> list[list[str]]:
    rows: list[list[str]] = []
    for cycle in range(LONG_CYCLES):
        ts = LONG_START + timedelta(minutes=72 * cycle)
        press = "PRS-A" if cycle % 2 == 0 else "PRS-B"
        days = (ts - LONG_START).total_seconds() / 86400
        for nest in range(1, LONG_NESTS + 1):
            piece = f"P{cycle:03d}{nest:02d}"
            for name, unit, nominal, lsl, usl, sd in LONG_VARIABLES:
                if sd is None:  # flatness: positive by nature
                    value = abs(rng.gauss(0.022, 0.009))
                else:
                    value = rng.gauss(nominal, sd)
                    if name == "Diametro_Pin" and nest == CRITICAL_NEST:
                        value += 0.013
                    if name == "Longitud_Terminal" and press == "PRS-B" and days > 2:
                        value += 0.012 * (days - 2) * 4
                spec_nok = (lsl is not None and value < lsl) or (usl is not None and value > usl)
                in_house_nok = name == "Planitud" and value > IN_HOUSE_FLATNESS_LIMIT
                rows.append(
                    [
                        ts.strftime("%d/%m/%Y"),
                        ts.strftime("%H:%M:%S"),
                        piece,
                        f"{cycle + 1}",
                        f"Nido {nest}",
                        press,
                        _shift(ts),
                        name,
                        _fmt(value),
                        unit,
                        "" if lsl is None else _fmt(lsl, 3),
                        _fmt(usl, 3),
                        "NOK" if spec_nok or in_house_nok else "OK",
                    ]
                )
    # Broken on purpose, so the quarantine summary has one row per reason.
    rows[5][8] = "n/a"  # non-numeric value
    rows[17][8] = ""  # empty value
    rows[29][0] = "31/02/2026"  # impossible date
    rows[41][9] = "in"  # unit differs from the rest of the variable
    rows.insert(60, list(rows[59]))  # duplicate piece + variable
    return rows


def _wide_rows(rng: random.Random) -> list[list[str]]:
    rows: list[list[str]] = []
    for cycle in range(WIDE_CYCLES):
        ts = WIDE_START + timedelta(minutes=19 * cycle)
        lot = "LOT-M1" if cycle < WIDE_CYCLES // 2 else "LOT-M2"
        for cav in range(1, WIDE_CAVITIES + 1):
            values = []
            for name, nominal, sd in WIDE_VARIABLES:
                if sd is None:
                    value = abs(rng.gauss(0.030, 0.014))
                else:
                    value = rng.gauss(nominal, sd)
                    if name == "WallThickness" and lot == "LOT-M2":
                        value -= 0.018  # second material lot runs thin
                    if name == "PinHeight" and cav == 3:
                        value += 0.016
                values.append(value)
            fail = (
                abs(values[0] - 2.5) > 0.03
                or abs(values[1] - 1.27) > 0.012
                or abs(values[2] - 22.0) > 0.06
                or abs(values[3] - 0.8) > 0.03
                or values[4] > 0.07
            )
            rows.append(
                [
                    ts.isoformat(timespec="seconds"),
                    f"SN-{cycle:04d}-{cav}",
                    f"CAV-{cav:02d}",
                    "PRS-C",
                    _shift(ts),
                    lot,
                    "FAIL" if fail else "PASS",
                    *(f"{v:.4f}" for v in values),
                ]
            )
    rows[8][8] = "ERR"  # non-numeric value -> whole piece quarantined
    rows[20][0] = "not-a-date"
    rows[33][7:] = [""] * len(WIDE_VARIABLES)  # piece without values
    return rows


def generate(output_dir: Path = OUTPUT_DIR) -> list[Path]:
    rng = random.Random(SEED)
    output_dir.mkdir(parents=True, exist_ok=True)
    long_path = output_dir / "mi_demo_dimensional_long.csv"
    with long_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, delimiter=";", lineterminator="\n")
        writer.writerow(
            [
                "Fecha",
                "Hora",
                "ID_Pieza",
                "Ciclo",
                "Nido",
                "Maquina",
                "Turno",
                "Caracteristica",
                "Valor",
                "Unidad",
                "LIE",
                "LSE",
                "Resultado",
            ]
        )
        writer.writerows(_long_rows(rng))
    wide_path = output_dir / "mi_demo_dimensional_wide.csv"
    with wide_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(
            [
                "timestamp",
                "serial",
                "cavity",
                "press",
                "shift",
                "material_lot",
                "result",
                *(name for name, _, _ in WIDE_VARIABLES),
            ]
        )
        writer.writerows(_wide_rows(rng))
    return [long_path, wide_path]


if __name__ == "__main__":
    for path in generate():
        print(f"Wrote {path}")
