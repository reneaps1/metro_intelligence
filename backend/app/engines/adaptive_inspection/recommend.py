"""F10.D (MI-47): adaptive inspection recommendation candidates.

CLAUDE.md §2 -- the single most important rule in this project: this engine
NEVER writes anything and NEVER changes an inspection frequency. It only
produces a *candidate* recommendation (type, human-readable rationale,
traceable evidence) for a service (outside this module, per this task's
scope) to persist as a Recommendation row in state='pending'. Whether a
recommendation ever takes effect is entirely a human decision through
F4.8's accept/reject flow -- the DB itself enforces that nothing reaches
catalog_inspection_frequencies without a recorded Decision (migration
0004's state machine).

Pure, deterministic, rule-based (CLAUDE.md §3/§22 -- no ML). Priority order
below is a real inspection-strategy judgment call, documented here because
nobody wrote an original brief for this task (see docs/tasks/F10.D.md):

1. An unvalidated recent process event outranks everything else -- until
   it's validated, every other signal about this characteristic is
   suspect.
2. A recent out-of-tolerance result demands immediate inspection regardless
   of the composite score -- a real defect already happened.
3. An elevated risk score with no confirmed defect yet is a "look into this
   now" signal (investigate_cause), not yet a frequency change.
4. Frequency changes (increase/decrease) are the least urgent category and
   require enough history to trust the signal -- decreasing inspection
   frequency in particular must never be recommended from a thin sample.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

RecommendationType = Literal[
    "frequency_increase",
    "frequency_decrease",
    "immediate_inspection",
    "investigate_cause",
    "post_event_validation",
]

ENGINE_NAME = "adaptive_inspection_engine"
ENGINE_VERSION = "v1"

# A process is only trusted to have its inspection frequency *decreased*
# once it has demonstrated stability over a real sample, not a handful of
# points -- deliberately more conservative than the minimum needed for a
# risk score itself (CLAUDE.md §2: never take this lightly).
MIN_HISTORY_FOR_FREQUENCY_DECREASE = 20
CAPABLE_CPK_THRESHOLD = Decimal("1.67")
MARGINAL_CPK_THRESHOLD = Decimal("1.0")


@dataclass(frozen=True)
class RiskSignal:
    """The subset of a computed RiskAssessment (F9.D) this engine needs,
    decoupled from the ORM model (CLAUDE.md §3: engines have no DB access).
    """

    risk_assessment_id: uuid.UUID
    characteristic_id: uuid.UUID
    score: int
    level: str
    cpk: Decimal | None
    recent_nok_count: int
    recent_result_count: int
    triggering_result_ids: list[uuid.UUID]
    recent_event_id: uuid.UUID | None = None
    recent_event_type: str | None = None


@dataclass(frozen=True)
class RecommendationCandidate:
    """Deliberately has no `state`/`decided_by`/frequency-value field: this
    is a candidate, not a decision or an operational change. The caller
    persists it as Recommendation(state='pending', ...)."""

    recommendation_type: RecommendationType
    rationale: str
    evidence: dict[str, Any]
    engine_name: str
    engine_version: str


def _evidence(signal: RiskSignal, **extra: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "risk_assessment_id": str(signal.risk_assessment_id),
        "characteristic_id": str(signal.characteristic_id),
        "score": signal.score,
        "level": signal.level,
        "triggering_result_ids": [str(rid) for rid in signal.triggering_result_ids],
    }
    if signal.cpk is not None:
        base["cpk"] = str(signal.cpk)
    base.update(extra)
    return base


def recommend(signal: RiskSignal) -> RecommendationCandidate | None:
    """Return at most one candidate recommendation for this characteristic,
    or None if nothing currently warrants one."""

    if signal.recent_event_id is not None:
        event_description = signal.recent_event_type or "a process event"
        return RecommendationCandidate(
            recommendation_type="post_event_validation",
            rationale=(
                f"A recent {event_description.replace('_', ' ')} needs validation before this "
                f"characteristic's other signals (risk score {signal.score}/100) can be trusted."
            ),
            evidence=_evidence(signal, event_id=str(signal.recent_event_id)),
            engine_name=ENGINE_NAME,
            engine_version=ENGINE_VERSION,
        )

    if signal.recent_nok_count >= 1:
        return RecommendationCandidate(
            recommendation_type="immediate_inspection",
            rationale=(
                f"{signal.recent_nok_count} out-of-tolerance result(s) in the last "
                f"{signal.recent_result_count} measurements -- inspect immediately to confirm "
                "the process is not producing defective parts."
            ),
            evidence=_evidence(signal),
            engine_name=ENGINE_NAME,
            engine_version=ENGINE_VERSION,
        )

    if signal.level in ("high", "critical"):
        return RecommendationCandidate(
            recommendation_type="investigate_cause",
            rationale=(
                f"Risk score is {signal.score}/100 ({signal.level}) with no confirmed defect yet -- "
                "investigate the root cause before it produces an out-of-tolerance part."
            ),
            evidence=_evidence(signal),
            engine_name=ENGINE_NAME,
            engine_version=ENGINE_VERSION,
        )

    if (
        signal.level == "low"
        and signal.cpk is not None
        and signal.cpk >= CAPABLE_CPK_THRESHOLD
        and signal.recent_result_count >= MIN_HISTORY_FOR_FREQUENCY_DECREASE
    ):
        return RecommendationCandidate(
            recommendation_type="frequency_decrease",
            rationale=(
                f"Cpk of {signal.cpk} and a risk score of {signal.score}/100 ({signal.level}) across "
                f"{signal.recent_result_count} measurements show a stable, capable process -- "
                "inspection frequency can safely decrease."
            ),
            evidence=_evidence(signal),
            engine_name=ENGINE_NAME,
            engine_version=ENGINE_VERSION,
        )

    if signal.level == "medium" and signal.cpk is not None and signal.cpk < MARGINAL_CPK_THRESHOLD:
        return RecommendationCandidate(
            recommendation_type="frequency_increase",
            rationale=(
                f"Cpk of {signal.cpk} and a risk score of {signal.score}/100 ({signal.level}) indicate "
                "marginal capability -- increase inspection frequency until the process demonstrates "
                "it is back in control."
            ),
            evidence=_evidence(signal),
            engine_name=ENGINE_NAME,
            engine_version=ENGINE_VERSION,
        )

    return None
