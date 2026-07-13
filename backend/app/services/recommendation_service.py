"""F4.8 (MI-28): the human decision flow over recommendations.

CLAUDE.md §2/§24: a recommendation never has operational effect on its own.
Accepting a frequency recommendation does not change the frequency directly
-- it inserts a Decision, and *only after that decision exists* does this
service insert a new, decision-linked InspectionFrequency version. The
insert order (Decision, then the Recommendation.state UPDATE) matches
migration 0004's trigger requirement exactly; the service also checks the
state itself before touching the DB, so a bad request gets a clear 409/422
instead of a raw trigger exception (docs/tasks/F4.8.md: "no confies solo en
el trigger de DB").
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalog import Characteristic, InspectionFrequency, InspectionPlan
from app.models.intelligence import ActionTaken, Decision, Recommendation
from app.services.audit_service import AuditContext, record_event

FREQUENCY_RECOMMENDATION_TYPES = frozenset({"frequency_increase", "frequency_decrease"})


class RecommendationNotFoundError(Exception):
    pass


class DecisionNotFoundError(Exception):
    pass


class InvalidStateTransitionError(Exception):
    """The recommendation isn't `pending`, so it cannot be decided again."""

    def __init__(self, current_state: str) -> None:
        self.current_state = current_state
        super().__init__(f"Recommendation is '{current_state}', not 'pending'; it cannot be decided.")


class MissingFrequencyEvidenceError(Exception):
    """A frequency recommendation's `evidence` must carry the proposed
    frequency (the contract F9.D/F10.D's generators are expected to
    populate) -- this is not a compliance/engine decision, just reading
    data that should already be there."""


class NoInspectionPlanError(Exception):
    pass


@dataclass(frozen=True)
class DecisionOutcome:
    decision: Decision
    recommendation: Recommendation
    superseded_recommendation_ids: list[uuid.UUID]
    inspection_frequency_id: uuid.UUID | None


def _resolve_inspection_plan(db: Session, part_number_id: uuid.UUID) -> InspectionPlan | None:
    stmt = (
        select(InspectionPlan)
        .where(InspectionPlan.part_number_id == part_number_id)
        .order_by(InspectionPlan.is_active.desc(), InspectionPlan.created_at)
    )
    return db.execute(stmt).scalars().first()


def _apply_frequency_recommendation(
    db: Session,
    *,
    recommendation: Recommendation,
    decision: Decision,
    user_id: uuid.UUID,
    context: AuditContext,
) -> uuid.UUID:
    characteristic = db.get(Characteristic, recommendation.characteristic_id)
    assert characteristic is not None  # FK guarantees this; recommendation can't outlive its characteristic

    plan = _resolve_inspection_plan(db, characteristic.part_number_id)
    if plan is None:
        raise NoInspectionPlanError(
            f"No inspection plan exists for part {characteristic.part_number_id}; "
            "cannot apply this frequency recommendation."
        )

    evidence = recommendation.evidence or {}
    frequency_type = evidence.get("proposed_frequency_type")
    frequency_value = evidence.get("proposed_frequency_value")
    if not frequency_type or frequency_value is None:
        raise MissingFrequencyEvidenceError(
            "Recommendation.evidence is missing 'proposed_frequency_type'/'proposed_frequency_value'."
        )

    active_stmt = select(InspectionFrequency).where(
        InspectionFrequency.inspection_plan_id == plan.id,
        InspectionFrequency.characteristic_id == characteristic.id,
        InspectionFrequency.valid_to.is_(None),
    )
    current = db.execute(active_stmt).scalar_one_or_none()

    new_frequency = InspectionFrequency(
        inspection_plan_id=plan.id,
        characteristic_id=characteristic.id,
        frequency_type=frequency_type,
        frequency_value=frequency_value,
        reason=decision.comment,
        changed_by_user_id=user_id,
        decision_id=decision.id,
    )
    db.add(new_frequency)

    if current is not None:
        before = {"frequency_type": current.frequency_type, "frequency_value": str(current.frequency_value)}
        current.valid_to = func.now()
        db.flush()
        record_event(
            db,
            context,
            action="close_version",
            entity_type="catalog.inspection_frequency",
            entity_id=current.id,
            before=before,
            after={"valid_to": "now"},
        )
    db.flush()
    record_event(
        db,
        context,
        action="create_version",
        entity_type="catalog.inspection_frequency",
        entity_id=new_frequency.id,
        after={
            "frequency_type": new_frequency.frequency_type,
            "frequency_value": str(new_frequency.frequency_value),
            "decision_id": str(decision.id),
        },
    )
    return new_frequency.id


def _supersede_related_pending(
    db: Session, recommendation: Recommendation, context: AuditContext
) -> list[uuid.UUID]:
    stmt = select(Recommendation).where(
        Recommendation.characteristic_id == recommendation.characteristic_id,
        Recommendation.recommendation_type == recommendation.recommendation_type,
        Recommendation.state == "pending",
        Recommendation.id != recommendation.id,
    )
    others = db.execute(stmt).scalars().all()
    superseded_ids = []
    for other in others:
        other.state = "superseded"
        db.flush()
        record_event(
            db,
            context,
            action="superseded",
            entity_type="intelligence.recommendation",
            entity_id=other.id,
            after={"state": "superseded", "superseded_by": str(recommendation.id)},
        )
        superseded_ids.append(other.id)
    return superseded_ids


def decide_recommendation(
    db: Session,
    *,
    recommendation_id: uuid.UUID,
    action: str,
    comment: str,
    user_id: uuid.UUID,
    context: AuditContext,
) -> DecisionOutcome:
    recommendation = db.execute(
        select(Recommendation).where(Recommendation.id == recommendation_id).with_for_update()
    ).scalar_one_or_none()
    if recommendation is None:
        raise RecommendationNotFoundError(str(recommendation_id))
    if recommendation.state != "pending":
        raise InvalidStateTransitionError(recommendation.state)

    before_state = recommendation.state
    decision = Decision(
        recommendation_id=recommendation.id,
        decided_by_user_id=user_id,
        action=action,
        comment=comment,
    )
    db.add(decision)
    db.flush()  # Decision must exist before the state UPDATE (migration 0004's trigger).

    recommendation.state = action
    db.flush()

    record_event(
        db,
        context,
        action="decided",
        entity_type="intelligence.recommendation",
        entity_id=recommendation.id,
        before={"state": before_state},
        after={"state": action, "decision_id": str(decision.id), "comment": comment},
    )

    inspection_frequency_id: uuid.UUID | None = None
    if action == "accepted" and recommendation.recommendation_type in FREQUENCY_RECOMMENDATION_TYPES:
        inspection_frequency_id = _apply_frequency_recommendation(
            db, recommendation=recommendation, decision=decision, user_id=user_id, context=context
        )

    superseded_ids = _supersede_related_pending(db, recommendation, context)

    db.commit()
    db.refresh(decision)
    db.refresh(recommendation)
    return DecisionOutcome(
        decision=decision,
        recommendation=recommendation,
        superseded_recommendation_ids=superseded_ids,
        inspection_frequency_id=inspection_frequency_id,
    )


def record_action_taken(
    db: Session,
    *,
    decision_id: uuid.UUID,
    description: str,
    outcome_status: str,
    observed_at: datetime | None,
    context: AuditContext,
) -> ActionTaken:
    decision = db.get(Decision, decision_id)
    if decision is None:
        raise DecisionNotFoundError(str(decision_id))

    action_taken = ActionTaken(
        decision_id=decision_id,
        description=description,
        outcome_status=outcome_status,
        observed_at=observed_at or (datetime.now(UTC) if outcome_status != "pending" else None),
    )
    db.add(action_taken)
    db.flush()

    record_event(
        db,
        context,
        action="create",
        entity_type="intelligence.action_taken",
        entity_id=action_taken.id,
        after={
            "decision_id": str(decision_id),
            "description": description,
            "outcome_status": outcome_status,
        },
    )
    db.commit()
    db.refresh(action_taken)
    return action_taken
