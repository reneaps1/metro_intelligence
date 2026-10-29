"""IQ-F19: private position specification for the REAL dataset.

The REAL export carries no nominals or tolerances (IQ-F10). For the X/Y
position plot an operator writes them, from the customer drawing, into a
PRIVATE JSON next to the converted dataset (plan decision D13) and points
`DEMO_REAL_SPEC_PATH` at it::

    {
      "format": "pin-spec-v1",
      "pin_pairs": [
        {"key": "pin_a", "label": "Pin A", "x": "<variable key>", "y": "<variable key>",
         "scale": 0.01, "nominal_x": 0.0, "nominal_y": 0.0, "tol_xy": 0.1,
         "circles": [{"label": "Plano", "diameter": 0.2}, {"label": "Fin de línea", "diameter": 0.3}]}
      ]
    }

`x` / `y` are variable keys of the converted dataset (its manifest), never
logger addresses. Pure: validated here, attached by the caller.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.engines.quality_analytics.dataset import PinPair, ToleranceCircle

MAX_SPEC_BYTES = 64 * 1024

_KEY = r"^[a-z][a-z0-9_]{0,31}$"


class _CircleIn(BaseModel):
    label: str = Field(min_length=1, max_length=48)
    diameter: float = Field(gt=0, lt=1_000)


class _PairIn(BaseModel):
    key: str = Field(pattern=_KEY)
    label: str = Field(min_length=1, max_length=64)
    x: str = Field(pattern=_KEY)
    y: str = Field(pattern=_KEY)
    scale: float = Field(default=1.0, gt=0)
    unit: str = Field(default="mm", max_length=16)
    nominal_x: float
    nominal_y: float
    tol_xy: float | None = Field(default=None, gt=0)
    circles: list[_CircleIn] = Field(default_factory=list, max_length=4)


class PinSpec(BaseModel):
    format: Literal["pin-spec-v1"]
    pin_pairs: list[_PairIn] = Field(min_length=1, max_length=24)


def read_pin_spec(path: Path) -> tuple[PinPair, ...]:
    """Raises OSError / ValueError / ValidationError when the file is unusable."""
    if path.stat().st_size > MAX_SPEC_BYTES:
        raise ValueError("pin spec file too large")
    spec = PinSpec.model_validate(json.loads(path.read_text(encoding="utf-8")))
    return tuple(
        PinPair(
            key=p.key,
            label=p.label,
            x=p.x,
            y=p.y,
            nominal_x=p.nominal_x,
            nominal_y=p.nominal_y,
            tol_xy=p.tol_xy,
            circles=tuple(ToleranceCircle(c.label, c.diameter) for c in p.circles),
            scale=p.scale,
            unit=p.unit,
        )
        for p in spec.pin_pairs
    )
