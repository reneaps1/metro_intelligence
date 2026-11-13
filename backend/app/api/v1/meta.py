"""IQ-F1: deployment metadata the frontend reads at runtime.

The edition is served from the backend (not baked into the frontend build as
a `VITE_*` variable) so a single Docker image can run as either edition.
Requires an authenticated session but no specific permission: every signed-in
role needs to know which navigation to render.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.edition import INDUSTRIAL_EDITION
from app.core.security import get_current_user
from app.models.security import User
from app.schemas.meta import MetaResponse

router = APIRouter(tags=["meta"])


@router.get("/meta", response_model=MetaResponse)
def read_meta(_user: User = Depends(get_current_user)) -> MetaResponse:
    settings = get_settings()
    industrial = settings.app_edition == INDUSTRIAL_EDITION
    return MetaResponse(
        edition=settings.app_edition,
        client_label=settings.demo_client_label if industrial else None,
        modules=["industrial_demo", "industrial_signals", "quality_analytics"] if industrial else [],
    )
