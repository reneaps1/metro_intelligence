"""IQ-F28 (plan decisions D18, D29): private product specification of one part.

Machine logs carry measured values and the machine's own verdict, but no
nominals or tolerances. An operator transcribes them from the customer's
drawing into a PRIVATE ``product.json`` next to the converted dataset
(`<private root>/<slug>/product.json`)::

    {
      "format": "product-spec-v1",
      "product": {"name": "...", "part_number": "...", "drawing": "... rev C",
                  "customer_program": "..."},
      "characteristics": [
        {"variable": "alt_pcb_1", "name": "Altura pin 1 lado PCB", "balloon": "12",
         "nominal": 9.5, "lsl": 9.4, "usl": 9.6, "unit": "mm", "class": "CC"}
      ]
    }

``variable`` is a variable key of the converted dataset. Every field but the
format and at least one of product / characteristics is optional. The
machine verdict stays the NOK basis (D10/D18): the limits only add
capability indices, specification lines and a machine-vs-drawing comparison.
Pure: validated here, applied by the caller. Never versioned in the repo.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.engines.quality_analytics.dataset import DimensionalDataset, Variable

MAX_PRODUCT_BYTES = 128 * 1024
_KEY = r"^[a-z][a-z0-9_]{0,31}$"


class ProductIn(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    part_number: str | None = Field(default=None, max_length=48)
    drawing: str | None = Field(default=None, max_length=80)
    customer_program: str | None = Field(default=None, max_length=48)


class CharacteristicIn(BaseModel):
    variable: str = Field(pattern=_KEY)
    name: str | None = Field(default=None, min_length=1, max_length=64)
    balloon: str | None = Field(default=None, max_length=12)
    nominal: float | None = None
    lsl: float | None = None
    usl: float | None = None
    unit: str | None = Field(default=None, max_length=16)
    char_class: str | None = Field(default=None, alias="class", max_length=12)

    @model_validator(mode="after")
    def _limits_ordered(self) -> CharacteristicIn:
        if self.lsl is not None and self.usl is not None and self.lsl >= self.usl:
            raise ValueError("lsl must be below usl")
        if self.nominal is not None and self.lsl is not None and self.nominal < self.lsl:
            raise ValueError("nominal must lie within the limits")
        if self.nominal is not None and self.usl is not None and self.nominal > self.usl:
            raise ValueError("nominal must lie within the limits")
        return self


class ProductSpec(BaseModel):
    format: Literal["product-spec-v1"]
    product: ProductIn = Field(default_factory=ProductIn)
    characteristics: list[CharacteristicIn] = Field(default_factory=list, max_length=400)

    @model_validator(mode="after")
    def _unique_variables(self) -> ProductSpec:
        keys = [c.variable for c in self.characteristics]
        if len(keys) != len(set(keys)):
            raise ValueError("a variable appears twice")
        return self


def read_product_spec(path: Path) -> ProductSpec:
    """Raises OSError / ValueError / ValidationError when the file is unusable."""
    if path.stat().st_size > MAX_PRODUCT_BYTES:
        raise ValueError("product file too large")
    return ProductSpec.model_validate(json.loads(path.read_text(encoding="utf-8")))


def apply_product_spec(dataset: DimensionalDataset, spec: ProductSpec) -> DimensionalDataset:
    """Return ``dataset`` with drawing names and limits on its variables.

    Raises ValueError when a characteristic names a variable the dataset does
    not have (a profile for another part must never be applied silently).
    Verdicts are untouched: the NOK basis stays the machine's.
    """
    by_key = {v.key: v for v in dataset.variables}
    unknown = [c.variable for c in spec.characteristics if c.variable not in by_key]
    if unknown:
        raise ValueError("product spec names variables the dataset does not have")
    chars = {c.variable: c for c in spec.characteristics}
    variables: list[Variable] = []
    for v in dataset.variables:
        c = chars.get(v.key)
        if c is None:
            variables.append(v)
            continue
        name = c.name or v.name
        if c.balloon:
            name = f"{name} (globo {c.balloon})"[:64]
        limited = Variable.from_limits(v.key, name, c.unit or v.unit, c.nominal, c.lsl, c.usl)
        variables.append(replace(limited, station=v.station))
    return replace(dataset, variables=tuple(variables))


def product_label(spec: ProductSpec | None, fallback: str) -> str:
    """Selector label: program · name (part number), else the operator's label."""
    if spec is None:
        return fallback
    p = spec.product
    head = " · ".join(x for x in (p.customer_program, p.name) if x)
    if not head:
        return fallback
    return f"{head} ({p.part_number})"[:64] if p.part_number else head[:64]
