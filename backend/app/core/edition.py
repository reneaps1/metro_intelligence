"""IQ-F1: edition gating (docs/tasks/IQ-plan-demo-industrial-quality.md, D5).

One codebase serves two deployable editions. Routers that only belong to the
industrial edition declare `require_industrial_edition` as a router-level
dependency, so in the metrology edition they answer 404 exactly as if they
did not exist -- fail-closed, and no hint that the module is there.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from app.core.config import get_settings

INDUSTRIAL_EDITION = "industrial"


def is_industrial_edition() -> bool:
    return get_settings().app_edition == INDUSTRIAL_EDITION


def require_industrial_edition() -> None:
    if not is_industrial_edition():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
