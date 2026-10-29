"""Source-agnostic, columnar dimensional dataset (IQ-F5).

One row per inspected piece; one value column per dimensional variable.
Columnar on purpose: aggregations loop over plain lists, which keeps tens of
thousands of pieces fast enough in pure Python. CSV imports (IQ-F6,
`app/connectors/dimensional_csv.py`) produce one of these; every analytic
works unchanged.
"""

from __future__ import annotations

from collections.abc import Sized
from dataclasses import dataclass, field
from typing import Literal

# IMPORTED = a user-uploaded file analysed as-is: not verified by the platform.
# REAL = the customer's closed historical period, converted offline and loaded
# locally from a private path (IQ-F10, plan decision D8).
SourceType = Literal["SIMULATED", "REAL", "IMPORTED"]
# "spec": a piece is NOK when a selected variable is out of tolerance.
# "reported": the machine's own verdicts (used when the source has no limits).
NokBasis = Literal["spec", "reported"]


@dataclass(frozen=True)
class Station:
    """An inspection station that reports its own OK/NOK verdict (IQ-F10)."""

    key: str
    name: str


@dataclass(frozen=True)
class Preset:
    """A named filter shortcut carried by the source (e.g. one station by nest)."""

    key: str
    label: str
    stations: tuple[str, ...]
    group_by: Literal["nest", "mold_cavity"] = "nest"


@dataclass(frozen=True)
class Variable:
    key: str
    name: str
    unit: str
    nominal: float
    # Tolerances relative to nominal; None = that side is not specified.
    lower_tol: float | None
    upper_tol: float | None
    # False when the source gave only limits: `nominal` is then just the
    # reference the tolerances are relative to and must not be shown as one.
    nominal_given: bool = True
    # Station that measures this variable, when the source says so (IQ-F10).
    station: str | None = None

    @classmethod
    def from_limits(
        cls, key: str, name: str, unit: str, nominal: float | None, lsl: float | None, usl: float | None
    ) -> Variable:
        """Build from absolute limits, as files usually carry them."""
        if nominal is not None:
            ref = nominal
        elif lsl is not None and usl is not None:
            ref = (lsl + usl) / 2
        else:
            ref = lsl if lsl is not None else usl if usl is not None else 0.0
        return cls(
            key,
            name,
            unit,
            ref,
            None if lsl is None else lsl - ref,
            None if usl is None else usl - ref,
            nominal_given=nominal is not None,
        )

    @property
    def display_nominal(self) -> float | None:
        return self.nominal if self.nominal_given else None

    @property
    def lsl(self) -> float | None:
        return None if self.lower_tol is None else self.nominal + self.lower_tol

    @property
    def usl(self) -> float | None:
        return None if self.upper_tol is None else self.nominal + self.upper_tol

    @property
    def has_tolerance(self) -> bool:
        return self.lower_tol is not None or self.upper_tol is not None

    def is_nok(self, value: float | None) -> bool:
        if value is None:
            return False
        lsl, usl = self.lsl, self.usl
        return (lsl is not None and value < lsl) or (usl is not None and value > usl)


@dataclass
class DimensionalDataset:
    id: str
    name: str
    description: str
    source_type: SourceType
    variables: tuple[Variable, ...]
    # --- per-piece columns (same length) ---
    timestamps: list[float]  # epoch seconds, ascending
    group_ids: list[int]  # inspection group / shot
    machines: list[str | None]
    cavities: list[int | None]
    shifts: list[str | None]
    batches: list[str | None]
    values: dict[str, list[float | None]]
    # Ground-truth notes for synthetic data ("verdad conocida"); empty for real data.
    mechanisms: list[str] = field(default_factory=list)
    # Piece verdict as reported by the source file (IQ-F6), kept apart from the
    # verdict recalculated from the specification; None = no such column.
    reported_nok: list[bool | None] | None = None
    # --- IQ-F10, all optional (None/empty = the dataset does not carry them) ---
    # Second grouping: the mold cavity, while `cavities` stays the nest.
    mold_cavities: list[int | None] | None = None
    # IQ-F17: the groupings exactly as the source reported them, kept next to
    # the normalized `cavities` / `mold_cavities` when a remap rule applied.
    nests_raw: list[int | None] | None = None
    mold_cavities_raw: list[int | None] | None = None
    # Stations in process order + their verdict per piece (True = NOK).
    stations: tuple[Station, ...] = ()
    station_nok: dict[str, list[bool | None]] = field(default_factory=dict)
    # Per-piece data-quality bit mask (see `connectors/long_signal_batch.py`).
    flags: list[int] | None = None
    # Plant local time = UTC + offset; used for day/hour buckets only.
    utc_offset_s: int = 0
    nok_basis: NokBasis = "spec"
    # False when pieces are not inspected in groups/shots (hides that KPI).
    has_groups: bool = True
    presets: tuple[Preset, ...] = ()
    # Counts only (no identifiers): what the offline conversion found.
    data_quality: dict[str, int] = field(default_factory=dict)
    nok: dict[str, list[bool]] = field(init=False)
    # First failing station in process order (None = no station failed).
    primary_fail: list[str | None] = field(init=False)

    def __post_init__(self) -> None:
        n = len(self.timestamps)
        columns: list[Sized] = [
            self.group_ids,
            self.machines,
            self.cavities,
            self.shifts,
            self.batches,
            *self.values.values(),
            *([self.reported_nok] if self.reported_nok is not None else []),
            *([self.mold_cavities] if self.mold_cavities is not None else []),
            *([self.nests_raw] if self.nests_raw is not None else []),
            *([self.mold_cavities_raw] if self.mold_cavities_raw is not None else []),
            *([self.flags] if self.flags is not None else []),
            *self.station_nok.values(),
        ]
        if any(len(col) != n for col in columns):
            raise ValueError("all dataset columns must have the same length")
        if {s.key for s in self.stations} != set(self.station_nok):
            raise ValueError("station_nok must carry exactly one column per station")
        by_key = {v.key: v for v in self.variables}
        # Variables without tolerance are never NOK by spec: share one read-only
        # column instead of evaluating every value (large real datasets).
        never: list[bool] = [False] * n
        self.nok = {
            key: [by_key[key].is_nok(x) for x in column] if by_key[key].has_tolerance else never
            for key, column in self.values.items()
        }
        order = [(s.key, self.station_nok[s.key]) for s in self.stations]
        self.primary_fail = (
            [next((key for key, col in order if col[i]), None) for i in range(n)] if order else [None] * n
        )

    def __len__(self) -> int:
        return len(self.timestamps)

    def variable(self, key: str) -> Variable:
        for v in self.variables:
            if v.key == key:
                return v
        raise KeyError(key)

    def distinct(self, column: list[str | None] | list[int | None]) -> list:
        return sorted({x for x in column if x is not None})

    def available_filters(self) -> dict[str, bool]:
        """A filter is offered only if the dataset actually carries that metadata."""
        return {
            "machine": any(m is not None for m in self.machines),
            "cavity": any(c is not None for c in self.cavities),
            "shift": any(s is not None for s in self.shifts),
            "batch": any(b is not None for b in self.batches),
            "mold_cavity": self.mold_cavities is not None and any(c is not None for c in self.mold_cavities),
            "station": bool(self.stations),
            "quality_flags": self.flags is not None and any(self.flags),
        }

    def station(self, key: str) -> Station:
        for s in self.stations:
            if s.key == key:
                return s
        raise KeyError(key)
