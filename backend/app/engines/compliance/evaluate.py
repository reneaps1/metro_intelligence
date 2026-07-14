"""F7.D (MI-44): pure OK/NOK compliance evaluation against a specification.

CLAUDE.md §3: engines are deterministic, rule-based, and pure -- this module
has no DB access. The caller (a service, never this module) is responsible
for loading the specification version that was actually in force when the
result was measured (CLAUDE.md §6 -- never re-evaluate against a later
version) and for persisting whatever this returns.

This engine's value as a separate, tested module (rather than each of
seed/generators/measurements.py and the F4.5 import pipeline reimplementing
the same three lines) is that the evaluation rule lives and is tested in
exactly one place, and that a re-evaluate-on-demand path (reports, audits)
has something authoritative to call.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

ENGINE_NAME = "compliance_engine"
ENGINE_VERSION = "v1"


@dataclass(frozen=True)
class SpecificationSnapshot:
    """The subset of a `Specification` row this engine needs, decoupled from
    the ORM model so the engine has no DB dependency (CLAUDE.md §3). At least
    one of lower_tol/upper_tol is non-None (enforced by the DB check
    constraint on catalog_specifications; not re-validated here)."""

    nominal: Decimal
    lower_tol: Decimal | None
    upper_tol: Decimal | None
    unit: str


@dataclass(frozen=True)
class ComplianceResult:
    deviation: Decimal
    is_ok: bool
    rationale: str
    engine_name: str
    engine_version: str


def evaluate(value: Decimal, spec: SpecificationSnapshot) -> ComplianceResult:
    """Evaluate one measured value against its specification.

    Convention (matches the existing seed generator, the only place this
    logic already lived before this engine existed):
    - ``deviation = value - nominal``.
    - A value exactly on a tolerance boundary is OK (inclusive bounds:
      ``deviation >= lower_tol``, ``deviation <= upper_tol``). This is a
      deliberate choice, not an accidental default: the tolerance limit
      itself is, by definition, still within spec in metrology practice.
    - A tolerance side that is ``None`` (unilateral characteristic) can never
      be violated on that side, regardless of how large the deviation is.
    """
    deviation = value - spec.nominal
    lower_ok = spec.lower_tol is None or deviation >= spec.lower_tol
    upper_ok = spec.upper_tol is None or deviation <= spec.upper_tol

    return ComplianceResult(
        deviation=deviation,
        is_ok=lower_ok and upper_ok,
        rationale=_rationale(deviation, spec, lower_ok=lower_ok, upper_ok=upper_ok),
        engine_name=ENGINE_NAME,
        engine_version=ENGINE_VERSION,
    )


def _rationale(deviation: Decimal, spec: SpecificationSnapshot, *, lower_ok: bool, upper_ok: bool) -> str:
    if lower_ok and upper_ok:
        return f"Within tolerance ({deviation:+} {spec.unit} from nominal)."
    if not upper_ok and spec.upper_tol is not None:
        over = deviation - spec.upper_tol
        return (
            f"{over} {spec.unit} above the upper tolerance limit "
            f"(deviation {deviation:+} {spec.unit}, limit +{spec.upper_tol} {spec.unit})."
        )
    if not lower_ok and spec.lower_tol is not None:
        under = spec.lower_tol - deviation
        return (
            f"{under} {spec.unit} below the lower tolerance limit "
            f"(deviation {deviation:+} {spec.unit}, limit {spec.lower_tol} {spec.unit})."
        )
    raise AssertionError("unreachable: is_ok is False but neither bound was violated")
