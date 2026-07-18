"""Phase 13 preview: wires the real Cpk-window series (already computed for
the "Cpk history" chart) into the experimental CUSUM drift engine.

Kept file-isolated from `capability_history_service.py` on purpose -- this
is the shadow-mode/experimental surface (CLAUDE.md §22), never the source of
an Alert or Recommendation. Reuses `compute_capability_history` rather than
a second parallel query, so a "why did this light up" question is always
answerable from the same real windows the Cpk history chart already shows.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.engines.experimental_ml.drift_cusum import DriftDetectionResult, detect_cusum_drift
from app.services.capability_history_service import compute_capability_history


def compute_experimental_drift(
    db: Session,
    characteristic_id: uuid.UUID,
    *,
    from_: datetime | None,
    to: datetime | None,
    window_size: int,
) -> DriftDetectionResult | None:
    windows = compute_capability_history(db, characteristic_id, from_=from_, to=to, window_size=window_size)
    cpk_values = [w.cpk for w in windows if w.cpk is not None]
    return detect_cusum_drift(cpk_values)
