"""F4.8 (MI-28): request/response schemas for recommendations and decisions.

CLAUDE.md §24 is the contract this whole module exists to enforce: no
recommendation has operational effect without an explicit, recorded human
decision. ``DecisionRequest`` requires a non-empty comment on purpose --
"accept" with no stated reason isn't the traceable decision §23/§24
requires.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


class RiskAssessmentSnapshot(BaseModel):
    id: uuid.UUID
    score: int
    level: str
    factors: dict[str, Any]
    engine_name: str
    engine_version: str
    computed_at: datetime

    model_config = {"from_attributes": True}


class ActionTakenRead(BaseModel):
    id: uuid.UUID
    description: str
    outcome_status: str
    observed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DecisionRead(BaseModel):
    id: uuid.UUID
    recommendation_id: uuid.UUID
    decided_by_user_id: uuid.UUID
    action: str
    comment: str | None
    decided_at: datetime
    actions_taken: list[ActionTakenRead]

    model_config = {"from_attributes": True}


class RecommendationRead(BaseModel):
    id: uuid.UUID
    characteristic_id: uuid.UUID
    recommendation_type: str
    rationale: str
    evidence: dict[str, Any]
    engine_name: str
    engine_version: str
    state: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecommendationDetailRead(RecommendationRead):
    risk_assessment: RiskAssessmentSnapshot | None
    decision: DecisionRead | None


class DecisionRequest(BaseModel):
    action: Literal["accepted", "rejected"]
    comment: str = Field(min_length=1, max_length=4000)


class DecisionResponse(BaseModel):
    decision: DecisionRead
    recommendation: RecommendationRead
    superseded_recommendation_ids: list[uuid.UUID]
    inspection_frequency_id: uuid.UUID | None


class ActionTakenCreate(BaseModel):
    description: str = Field(min_length=1, max_length=4000)
    outcome_status: Literal["pending", "effective", "ineffective", "not_applicable"] = "pending"
    observed_at: datetime | None = None


class AlertRead(BaseModel):
    """Live Monitor alarm fix (2026-07): a real, engine-attributed alarm --
    see `app.engines.spc.alarm_rules` for what triggers one and
    `app.services.alarm_detection_service` for how it's persisted."""

    id: uuid.UUID
    characteristic_id: uuid.UUID
    severity: str
    trigger_type: str
    trigger_id: uuid.UUID
    message: str
    rationale: str
    computed_inputs: dict[str, Any]
    engine_name: str
    engine_version: str
    created_at: datetime
    delivered_at: datetime | None
    acknowledged_at: datetime | None
    acknowledged_by_user_id: uuid.UUID | None

    model_config = {"from_attributes": True}
