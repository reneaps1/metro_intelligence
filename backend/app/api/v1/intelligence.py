"""F4.8 (MI-28): recommendations inbox, human decision, and Decision Memory
action-taken recording. CLAUDE.md §24 -- nothing here changes production
behavior on its own; see app.services.recommendation_service's docstring."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import require_permission
from app.models.intelligence import Decision, Recommendation
from app.models.security import User
from app.schemas.intelligence import (
    ActionTakenCreate,
    ActionTakenRead,
    DecisionRead,
    DecisionRequest,
    DecisionResponse,
    Page,
    RecommendationDetailRead,
    RecommendationRead,
)
from app.services.audit_service import AuditContext, get_audit_context
from app.services.recommendation_service import (
    DecisionNotFoundError,
    InvalidStateTransitionError,
    MissingFrequencyEvidenceError,
    NoInspectionPlanError,
    RecommendationNotFoundError,
    decide_recommendation,
    record_action_taken,
)

router = APIRouter(tags=["intelligence"])


@router.get("/recommendations", response_model=Page[RecommendationRead])
def list_recommendations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    state: str | None = None,
    characteristic_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("intelligence.recommendation", "read")),
) -> Page[RecommendationRead]:
    filtered = select(Recommendation)
    if state is not None:
        filtered = filtered.where(Recommendation.state == state)
    if characteristic_id is not None:
        filtered = filtered.where(Recommendation.characteristic_id == characteristic_id)

    total = db.execute(select(func.count()).select_from(filtered.subquery())).scalar_one()
    page_stmt = (
        filtered.order_by(Recommendation.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
    )
    rows = db.execute(page_stmt).scalars().all()
    return Page(
        items=[RecommendationRead.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/recommendations/{recommendation_id}", response_model=RecommendationDetailRead)
def get_recommendation(
    recommendation_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("intelligence.recommendation", "read")),
) -> RecommendationDetailRead:
    stmt = (
        select(Recommendation)
        .where(Recommendation.id == recommendation_id)
        .options(
            selectinload(Recommendation.risk_assessment),
            selectinload(Recommendation.decision).selectinload(Decision.actions_taken),
        )
    )
    recommendation = db.execute(stmt).unique().scalar_one_or_none()
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")
    return RecommendationDetailRead.model_validate(recommendation)


@router.post("/recommendations/{recommendation_id}/decision", response_model=DecisionResponse)
def decide(
    recommendation_id: uuid.UUID,
    payload: DecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("intelligence.recommendation", "decide")),
    context: AuditContext = Depends(get_audit_context),
) -> DecisionResponse:
    try:
        outcome = decide_recommendation(
            db,
            recommendation_id=recommendation_id,
            action=payload.action,
            comment=payload.comment,
            user_id=current_user.id,
            context=context,
        )
    except RecommendationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found."
        ) from exc
    except InvalidStateTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except NoInspectionPlanError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except MissingFrequencyEvidenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return DecisionResponse(
        decision=DecisionRead.model_validate(outcome.decision),
        recommendation=RecommendationRead.model_validate(outcome.recommendation),
        superseded_recommendation_ids=outcome.superseded_recommendation_ids,
        inspection_frequency_id=outcome.inspection_frequency_id,
    )


@router.post(
    "/decisions/{decision_id}/actions",
    response_model=ActionTakenRead,
    status_code=status.HTTP_201_CREATED,
)
def create_action_taken(
    decision_id: uuid.UUID,
    payload: ActionTakenCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("intelligence.action_taken", "create")),
    context: AuditContext = Depends(get_audit_context),
) -> ActionTakenRead:
    try:
        action_taken = record_action_taken(
            db,
            decision_id=decision_id,
            description=payload.description,
            outcome_status=payload.outcome_status,
            observed_at=payload.observed_at,
            context=context,
        )
    except DecisionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found.") from exc
    return ActionTakenRead.model_validate(action_taken)
