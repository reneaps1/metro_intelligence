"""EXPERIMENTAL: orchestrates the Thompson-Sampling adaptive sampling
recommender over real Cpk-window history (reusing
`compute_capability_history`, never a second parallel query -- same
convention as `drift_detection_service.py`), cross-checked against the real
Recommendation table for the same characteristic. Read-only end to end:
never writes/mutates a Recommendation/Decision row.

Every log line here is prefixed "[EXPERIMENTAL]" -- a deliberate,
locally-scoped convention for this one shadow-mode module only (no other
service in this repo logs at all today), mirroring how
`drift_cusum.ENGINE_VERSION = "v1-experimental"` marks that engine as
experimental via a different mechanism.
"""

from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.adaptive_sampling import (
    AdaptiveSamplingConfig,
    ExistingRecommendationSignal,
    detect_conflicts,
    recommend_sampling_frequency,
)
from app.models.intelligence import Recommendation
from app.schemas.measurements import SamplingRecommendation
from app.services.capability_history_service import compute_capability_history

logger = logging.getLogger(__name__)


def _fetch_existing_recommendations(
    db: Session, characteristic_id: uuid.UUID
) -> list[ExistingRecommendationSignal]:
    """Mirrors `app.api.v1.intelligence.list_recommendations`'s own
    characteristic_id filter -- every state included, `detect_conflicts`
    itself decides which states are active."""
    stmt = select(Recommendation).where(Recommendation.characteristic_id == characteristic_id)
    rows = db.execute(stmt).scalars().all()
    return [
        ExistingRecommendationSignal(
            id=row.id,
            recommendation_type=row.recommendation_type,
            state=row.state,
            rationale=row.rationale,
        )
        for row in rows
    ]


def compute_adaptive_sampling_recommendation(
    db: Session,
    characteristic_id: uuid.UUID,
    *,
    from_: datetime | None,
    to: datetime | None,
    window_size: int,
    config: AdaptiveSamplingConfig | None = None,
    rng: random.Random | None = None,
) -> SamplingRecommendation:
    """Never raises for thin/empty/null Cpk history -- the engine's own
    `windows_analyzed < minimum_windows` branch handles that. `rng`/`config`
    are exposed only for tests; the real endpoint never passes them
    (production uses a fresh, unseeded `random.Random()` per call, and the
    engine's default config)."""
    logger.info(
        "[EXPERIMENTAL] computing adaptive sampling recommendation for characteristic_id=%s",
        characteristic_id,
    )

    windows = compute_capability_history(db, characteristic_id, from_=from_, to=to, window_size=window_size)
    cpk_values = [w.cpk for w in windows if w.cpk is not None]

    result = recommend_sampling_frequency(cpk_values, config=config, rng=rng)

    existing = _fetch_existing_recommendations(db, characteristic_id)
    conflicts = detect_conflicts(existing, result.recommended_frequency)
    if conflicts:
        logger.info(
            "[EXPERIMENTAL] %d conflicting existing recommendation(s) for characteristic_id=%s",
            len(conflicts),
            characteristic_id,
        )

    current_cpk = float(cpk_values[-1]) if cpk_values else 0.0

    return SamplingRecommendation(
        characteristic_id=str(characteristic_id),
        recommended_frequency=result.recommended_frequency,
        current_cpk=current_cpk,
        cpk_trend=result.cpk_trend,
        confidence=result.confidence,
        windows_analyzed=result.windows_analyzed,
        conflicting_recommendations=[
            {
                "id": str(c.id),
                "type": c.type,
                "status": c.status,
                "title": c.title,
                "reason": c.reason,
                "conflict_reason": c.conflict_reason,
            }
            for c in conflicts
        ]
        or None,
    )
