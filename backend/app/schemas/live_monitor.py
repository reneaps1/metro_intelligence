"""LM.3 (docs/tasks/LM3-live-monitor-presenter-controls.md): REST schema for
the scenario-candidates lookup. The WebSocket event schemas (`point`,
`control_limits_updated`) from LM.1 aren't modeled here -- FastAPI/Pydantic
don't describe WS payloads the way they do REST, and `app.api.v1.live_monitor`
serializes those by hand already.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class ScenarioCandidatesResponse(BaseModel):
    scenario: str
    candidate_pool_size: int
    characteristic_ids: list[uuid.UUID]
