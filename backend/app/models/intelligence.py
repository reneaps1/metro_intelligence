from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, uuid7


class RiskAssessment(Base):
    __tablename__ = "intelligence_risk_assessments"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_intelligence_risk_assessments_score_range"),
        CheckConstraint("level IN ('low', 'medium', 'high', 'critical')", name="ck_intelligence_risk_assessments_level"),
        Index("ix_intelligence_risk_assessments_characteristic_id", "characteristic_id", "computed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    characteristic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_characteristics.id", ondelete="RESTRICT"), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    factors: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    engine_name: Mapped[str] = mapped_column(String(64), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    recommendations: Mapped[list[Recommendation]] = relationship(back_populates="risk_assessment")


class Recommendation(Base):
    """Mutable only through the state machine enforced by migration 0004's
    trigger: `pending` is the only non-terminal state, and `accepted`/
    `rejected` require a matching Decision to already exist."""

    __tablename__ = "intelligence_recommendations"
    __table_args__ = (
        CheckConstraint(
            "recommendation_type IN ('frequency_increase', 'frequency_decrease', 'immediate_inspection', 'investigate_cause', 'post_event_validation')",
            name="ck_intelligence_recommendations_type",
        ),
        CheckConstraint(
            "state IN ('pending', 'accepted', 'rejected', 'superseded', 'expired')",
            name="ck_intelligence_recommendations_state",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    characteristic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_characteristics.id", ondelete="RESTRICT"), nullable=False
    )
    risk_assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("intelligence_risk_assessments.id", ondelete="SET NULL"), nullable=True
    )
    recommendation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    engine_name: Mapped[str] = mapped_column(String(64), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    risk_assessment: Mapped[RiskAssessment | None] = relationship(back_populates="recommendations")
    decision: Mapped[Decision | None] = relationship(back_populates="recommendation")


class Decision(Base):
    """Append-only (migration 0004 trigger blocks UPDATE/DELETE), mirroring
    security_audit_log. One decision per recommendation."""

    __tablename__ = "intelligence_decisions"
    __table_args__ = (
        CheckConstraint("action IN ('accepted', 'rejected')", name="ck_intelligence_decisions_action"),
        UniqueConstraint("recommendation_id", name="uq_intelligence_decisions_recommendation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("intelligence_recommendations.id", ondelete="RESTRICT"), nullable=False
    )
    decided_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("security_users.id", ondelete="RESTRICT"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    recommendation: Mapped[Recommendation] = relationship(back_populates="decision")
    actions_taken: Mapped[list[ActionTaken]] = relationship(back_populates="decision")


class ActionTaken(Base):
    """Append-only (migration 0004 trigger). Closes the Decision Memory loop:
    what was actually done and, once known, its observed outcome."""

    __tablename__ = "intelligence_action_taken"
    __table_args__ = (
        CheckConstraint(
            "outcome_status IN ('pending', 'effective', 'ineffective', 'not_applicable')",
            name="ck_intelligence_action_taken_outcome_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    decision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("intelligence_decisions.id", ondelete="RESTRICT"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    outcome_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    decision: Mapped[Decision] = relationship(back_populates="actions_taken")


class Alert(Base):
    """Mutable delivery/read state (`delivered_at`, `read_at`) — not
    append-only like Decision/ActionTaken, since marking an alert read is a
    legitimate update. `trigger_id` is a bare column (polymorphic reference
    across recommendation/risk_assessment/process_event/measurement result),
    no FK -- `characteristic_id`, by contrast, is a direct FK, since every
    Live Monitor alarm (`app.engines.spc.alarm_rules`) is always
    characteristic-scoped.

    `acknowledged_at`/`acknowledged_by_user_id` are this alert type's
    "read/acknowledged" update (rbac.md: `intelligence.alert.update`) --
    `acknowledged_at IS NULL` means "open", the dedup key
    `alarm_detection_service.record_alarm_if_new` checks before opening a
    second alert for the same characteristic + rule."""

    __tablename__ = "intelligence_alerts"
    __table_args__ = (
        CheckConstraint("severity IN ('info', 'warning', 'critical')", name="ck_intelligence_alerts_severity"),
        CheckConstraint(
            "trigger_type IN ('recommendation', 'risk_assessment', 'process_event', "
            "'compliance_violation', 'capability_below_threshold')",
            name="ck_intelligence_alerts_trigger_type",
        ),
        Index("ix_intelligence_alerts_created_at", "created_at"),
        Index("ix_intelligence_alerts_characteristic_id", "characteristic_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    target_roles: Mapped[list[str]] = mapped_column(ARRAY(String(32)), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    characteristic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_characteristics.id", ondelete="RESTRICT"), nullable=False
    )
    engine_name: Mapped[str] = mapped_column(String(64), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    computed_inputs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("security_users.id", ondelete="SET NULL"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
