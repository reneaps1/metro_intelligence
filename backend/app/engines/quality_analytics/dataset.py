"""Source-agnostic, columnar dimensional dataset (IQ-F5).

One row per inspected piece; one value column per dimensional variable.
Columnar on purpose: aggregations loop over plain lists, which keeps tens of
thousands of pieces fast enough in pure Python. CSV imports (IQ-F6,
`app/connectors/dimensional_csv.py`) produce one of these; every analytic
works unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# IMPORTED = a user-uploaded file analysed as-is: not verified by the platform.
SourceType = Literal["SIMULATED", "REAL", "IMPORTED"]


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
    nok: dict[str, list[bool]] = field(init=False)

    def __post_init__(self) -> None:
        n = len(self.timestamps)
        columns = [
            self.group_ids,
            self.machines,
            self.cavities,
            self.shifts,
            self.batches,
            *self.values.values(),
            *([self.reported_nok] if self.reported_nok is not None else []),
        ]
        if any(len(col) != n for col in columns):
            raise ValueError("all dataset columns must have the same length")
        by_key = {v.key: v for v in self.variables}
        self.nok = {key: [by_key[key].is_nok(x) for x in column] for key, column in self.values.items()}

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
        }
