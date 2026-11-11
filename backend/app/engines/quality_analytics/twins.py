"""IQ-F26 (plan decision D23): fictitious "twin" parts for the public demo's part selector.

Each twin copies the SHAPE of a production line the demo was built for --
stations in process order, number of pins, grouping slots (cavity, or nest +
side), reported OK/NOK verdicts with the first failing station, NOK waves
localized to one group, a persistently weaker group and line stops -- with
INVENTED values. No number here was computed from customer data; limits are
round fictitious values. Every twin is `SIMULATED` and labelled as a twin.

Generated deterministically in memory (no files, nothing to version), small
enough for a 512 MB instance: ~15k pieces per part.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache

from app.engines.quality_analytics.dataset import DimensionalDataset, Station, Variable

TWIN_PREFIX = "demo-"
GENERATOR_VERSION = "twin-1.0.0"
TWIN_NOTE = "Gemelo sintético: estructura de una línea real, valores ficticios."
START_TS = 1_790_000_000.0  # fixed fictitious start (epoch s)
UTC_OFFSET_S = -6 * 3600


@dataclass(frozen=True)
class TwinVar:
    key: str
    name: str
    station: str
    mean: float
    sd: float
    lsl: float | None
    usl: float | None
    unit: str = "mm"
    absolute: bool = False  # deviations reported as magnitudes (>= 0)


@dataclass(frozen=True)
class TwinSpec:
    slug: str
    label: str
    line: str
    description: str
    order: int
    seed: int
    stations: tuple[tuple[str, str], ...]
    variables: tuple[TwinVar, ...]
    # Verdict-only stations: base NOK probability per piece.
    verdict_only: tuple[tuple[str, float], ...]
    groups: tuple[int, ...]
    primary_label: str
    sides: bool  # two pieces per cycle (left/right) in the secondary slot
    pieces: int
    cycle_s: float
    weak_group: int
    wave_variable: str


def _heights(prefix: str, name: str, station: str, n: int, mean: float) -> list[TwinVar]:
    return [
        TwinVar(f"{prefix}_{i}", f"{name} · pin {i}", station, mean, 0.035, mean - 0.15, mean + 0.15)
        for i in range(1, n + 1)
    ]


def _deviation(prefix: str, name: str, station: str, n: int, mean: float, usl: float) -> list[TwinVar]:
    return [
        TwinVar(f"{prefix}_{i}", f"{name} {i}", station, mean, mean * 0.55, None, usl, absolute=True)
        for i in range(1, n + 1)
    ]


def _line_b(slug: str, label: str, pins: int, groups: range, order: int, seed: int, conn: float) -> TwinSpec:
    xy = [
        v
        for i in range(1, pins + 1)
        for v in (
            TwinVar(
                f"pos_con_x_{i}", f"Desviación X · pin {i}", "pos_con", 0.09, 0.05, None, 0.36, absolute=True
            ),
            TwinVar(
                f"pos_con_y_{i}", f"Desviación Y · pin {i}", "pos_con", 0.13, 0.06, None, 0.36, absolute=True
            ),
        )
    ]
    return TwinSpec(
        slug=slug,
        label=label,
        line="Línea demo B · fin de línea con serie",
        description=(
            f"Gemelo ficticio de una celda de pruebas de fin de línea ({pins} pines). "
            "Una fila por pieza unida por número de serie; veredictos de cada prueba."
        ),
        order=order,
        seed=seed,
        stations=(
            ("alt_pcb", "Altura de pines · lado PCB"),
            ("alt_con", "Altura de pines · lado conector"),
            ("tipo", "Verificación de tipo"),
            ("pos_pcb", "Posición de pines · lado PCB"),
            ("pos_con", "Posición de pines · lado conector"),
        ),
        variables=(
            *_heights("alt_pcb", "Altura PCB", "alt_pcb", pins, 9.70),
            *_heights("alt_con", "Altura conector", "alt_con", pins, conn),
            *_deviation("pos_pcb", "Radio de posición · pin", "pos_pcb", pins, 0.12, 0.38),
            *xy,
        ),
        verdict_only=(("tipo", 0.0012),),
        groups=tuple(groups),
        primary_label="Cavidad",
        sides=False,
        pieces=15_000,
        cycle_s=13.0,
        weak_group=tuple(groups)[2],
        wave_variable="pos_pcb_3",
    )


def _line_a(slug: str, label: str, order: int, seed: int, long_mean: float) -> TwinSpec:
    return TwinSpec(
        slug=slug,
        label=label,
        line="Línea demo A · mesa indexada sin serie",
        description=(
            "Gemelo ficticio de una mesa indexada de 12 nidos con dos lados por ciclo y sin número de "
            "serie: la pieza se sigue por nido, lado y tiempo."
        ),
        order=order,
        seed=seed,
        stations=(
            ("longitud", "Longitud de pines"),
            ("alto_voltaje", "Prueba de alto voltaje"),
            ("vision_con", "Visión · lado conector"),
            ("vision_pcb", "Visión · lado PCB"),
            ("codigo", "Lectura de código"),
        ),
        variables=(
            *[
                TwinVar(
                    f"long_{i}",
                    f"Longitud · pin {i}",
                    "longitud",
                    long_mean,
                    0.04,
                    long_mean - 0.15,
                    long_mean + 0.15,
                )
                for i in range(1, 6)
            ],
            *[
                TwinVar(f"long_corto_{i}", f"Longitud · pin corto {i}", "longitud", 6.90, 0.04, 6.76, 7.04)
                for i in range(1, 3)
            ],
            *_deviation("giro_con", "Giro lado conector", "vision_con", 2, 0.20, 0.56),
            *_deviation("giro_pcb", "Giro lado PCB", "vision_pcb", 5, 0.15, 0.45),
        ),
        verdict_only=(("alto_voltaje", 0.0006), ("codigo", 0.004)),
        groups=tuple(range(1, 13)),
        primary_label="Nido",
        sides=True,
        pieces=15_000,
        cycle_s=14.0,
        weak_group=9,
        wave_variable="giro_pcb_2",
    )


TWINS: dict[str, TwinSpec] = {
    s.slug: s
    for s in (
        _line_b("linea-b-familia-9", "MI-DEMO-B1 · familia 9 pines", 9, range(17, 25), 10, 101, 6.40),
        _line_b("linea-b-familia-8a", "MI-DEMO-B2 · familia 8 pines", 8, range(9, 17), 11, 102, 5.40),
        _line_b("linea-b-familia-8b", "MI-DEMO-B3 · familia 8 pines", 8, range(9, 17), 12, 103, 5.45),
        _line_a("linea-a-tipo-1", "MI-DEMO-A1 · tipo 1", 20, 201, 10.50),
        _line_a("linea-a-tipo-2", "MI-DEMO-A2 · tipo 2", 21, 202, 10.45),
    )
}


def twin_ids() -> list[str]:
    return [f"{TWIN_PREFIX}{slug}" for slug in sorted(TWINS, key=lambda s: (TWINS[s].order, s))]


def twin_spec(dataset_id: str) -> TwinSpec | None:
    if not dataset_id.startswith(TWIN_PREFIX):
        return None
    return TWINS.get(dataset_id[len(TWIN_PREFIX) :])


def _shift(ts: float) -> str:
    hour = int(((ts + UTC_OFFSET_S) % 86_400) // 3_600)
    return "T1" if 6 <= hour < 14 else "T2" if 14 <= hour < 22 else "T3"


def _timestamps(rng: random.Random, spec: TwinSpec, cycles: int) -> list[float]:
    """Cycle times with jitter and a few line stops (20 min to 3 h)."""
    out: list[float] = []
    t = START_TS
    stops = sorted(rng.sample(range(200, cycles - 200), 6))
    for c in range(cycles):
        if stops and c == stops[0]:
            stops.pop(0)
            t += rng.uniform(20 * 60, 3 * 3600)
        t += spec.cycle_s * rng.uniform(0.85, 1.25)
        out.append(round(t, 1))
    return out


@lru_cache(maxsize=8)
def build_twin(slug: str) -> DimensionalDataset:
    spec = TWINS[slug]
    rng = random.Random(spec.seed)
    per_cycle = 2 if spec.sides else 1
    cycles = spec.pieces // per_cycle
    cycle_ts = _timestamps(rng, spec, cycles)
    n = cycles * per_cycle
    # Two NOK waves: one group drifts on one variable for a few hundred pieces.
    waves = [
        (start, start + rng.randint(250, 450), rng.choice(spec.groups))
        for start in sorted(rng.sample(range(n // 6, n - n // 6), 2))
    ]
    station_keys = [k for k, _ in spec.stations]
    vars_by_station: dict[str, list[TwinVar]] = {k: [] for k in station_keys}
    for v in spec.variables:
        vars_by_station[v.station].append(v)
    verdict_only = dict(spec.verdict_only)

    timestamps: list[float] = []
    groups: list[int | None] = []
    sides: list[int | None] = []
    values: dict[str, list[float | None]] = {v.key: [] for v in spec.variables}
    station_nok: dict[str, list[bool | None]] = {k: [] for k in station_keys}
    reported: list[bool | None] = []
    burst_start = rng.randint(n // 3, n // 2)

    for i in range(n):
        cycle = i // per_cycle
        group = spec.groups[cycle % len(spec.groups)]
        timestamps.append(cycle_ts[cycle])
        groups.append(group)
        sides.append((i % per_cycle) + 1 if spec.sides else None)
        failed = False
        for key in station_keys:
            if failed:
                station_nok[key].append(None)
                for v in vars_by_station[key]:
                    values[v.key].append(None)
                continue
            nok = False
            for v in vars_by_station[key]:
                shift = 0.0
                if group == spec.weak_group:
                    shift += 1.1 * v.sd
                if v.key == spec.wave_variable:
                    for start, end, wave_group in waves:
                        if start <= i < end and group == wave_group:
                            shift += 4.5 * v.sd * min(1.0, (i - start) / 80)
                x = rng.gauss(v.mean + shift, v.sd)
                if v.absolute:
                    x = abs(x)
                x = round(x, 4)
                values[v.key].append(x)
                if (v.lsl is not None and x < v.lsl) or (v.usl is not None and x > v.usl):
                    nok = True
            if key in verdict_only:
                p = verdict_only[key] * (12 if burst_start <= i < burst_start + 120 else 1)
                nok = nok or rng.random() < p
            station_nok[key].append(nok)
            failed = nok
        reported.append(failed)

    variables = tuple(_variable(v) for v in spec.variables)
    return DimensionalDataset(
        id=f"{TWIN_PREFIX}{slug}",
        name=spec.label,
        description=f"{spec.description} {TWIN_NOTE}",
        source_type="SIMULATED",
        variables=variables,
        timestamps=timestamps,
        group_ids=list(range(n)),
        machines=[None] * n,
        cavities=groups,
        shifts=[_shift(t) for t in timestamps],
        batches=[None] * n,
        values=values,
        mechanisms=[
            f"{spec.primary_label} {spec.weak_group} ligeramente desplazada en todas las cotas.",
            *[
                f"Oleada NOK en {spec.primary_label.lower()} {g}: deriva de «{spec.wave_variable}» "
                f"en las piezas {s}–{e}."
                for s, e, g in waves
            ],
        ],
        reported_nok=reported,
        mold_cavities=sides if spec.sides else None,
        stations=tuple(Station(k, name) for k, name in spec.stations),
        station_nok=station_nok,
        flags=[0] * n,
        utc_offset_s=UTC_OFFSET_S,
        nok_basis="reported",
        has_groups=False,
        data_quality={"pieces": n},
    )


def _variable(v: TwinVar) -> Variable:
    base = Variable.from_limits(v.key, v.name, v.unit, None, v.lsl, v.usl)
    return Variable(
        base.key,
        base.name,
        base.unit,
        base.nominal,
        base.lower_tol,
        base.upper_tol,
        nominal_given=False,
        station=v.station,
    )


def twin_meta(dataset_id: str) -> tuple[str, dict[str, str], tuple[str, ...]] | None:
    """(line, group labels, assumptions) for the selector."""
    spec = twin_spec(dataset_id)
    if spec is None:
        return None
    labels = {"primary": spec.primary_label}
    if spec.sides:
        labels["secondary"] = "Lado"
    return spec.line, labels, (TWIN_NOTE, "Hora y turnos ficticios.")
