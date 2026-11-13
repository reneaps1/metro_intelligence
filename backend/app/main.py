"""F4.1 (MI-21): app entrypoint. `app.main:app` is the contract
backend/Dockerfile's CMD relies on -- keep that name and attribute stable."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware
from app.core.ratelimit import limiter

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="Metro Intelligence API")

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# F4.2 (MI-22): rate limiting on /auth/* (and any future limited route).
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

register_exception_handlers(app)

app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
def warm_up_real_dataset() -> None:
    # IQ-F10/F21: parse the dataset the part selector opens with, off the request path.
    if settings.app_edition == "industrial":
        from app.services.dataset_registry import warm_up_in_background

        warm_up_in_background()

@app.on_event("startup")
def create_demo_admin():
    import os
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from app.core.password import hash_password
    from app.models import User, Role, UserRole

    password = os.getenv("SEED_DEMO_USER_PASSWORD")
    if not password or settings.app_env == "production":
        return

    engine = create_engine(settings.database_url)

    with Session(engine) as session:
        existing = session.scalar(
            select(User).where(User.email == "luis.torres@demo.local")
        )
        if existing:
            # IQ-F30: explicit, audited operator recovery (see app/services/demo_admin.py).
            if os.getenv("SEED_DEMO_USER_RESET", "").lower() == "true":
                from app.services.demo_admin import reset_demo_admin

                reset_demo_admin(session, existing.email, password)
            return

        role = session.scalar(
            select(Role).where(Role.name == "admin")
        )
        if role is None:
            raise RuntimeError("Admin role not found")

        user = User(
            email="luis.torres@demo.local",
            display_name="Luis Torres",
            password_hash=hash_password(password),
            is_active=True,
        )
        user.roles.append(UserRole(role=role))
        session.add(user)
        session.commit()


@app.on_event("startup")
def reset_demo_passwords() -> None:
    """Operator action on a demo host (app/services/demo_admin.py): with
    SEED_DEMO_USERS_RESET_ALL=true, every user gets SEED_DEMO_USER_PASSWORD."""
    import logging
    import os

    if os.getenv("SEED_DEMO_USERS_RESET_ALL", "").lower() != "true" or settings.app_env == "production":
        return
    logger = logging.getLogger(__name__)
    password = os.getenv("SEED_DEMO_USER_PASSWORD")
    if not password:
        logger.error("SEED_DEMO_USERS_RESET_ALL is set but SEED_DEMO_USER_PASSWORD is not; nothing changed.")
        return

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.services.demo_admin import reset_all_demo_passwords

    try:
        with Session(create_engine(settings.database_url)) as session:
            changed = reset_all_demo_passwords(session, password)
    except ValueError as exc:
        # A password that breaks the policy must not take the service down.
        logger.error("Demo passwords not reset: %s", exc)
        return
    logger.info("Demo passwords reset for %s users. Unset SEED_DEMO_USERS_RESET_ALL.", changed)


@app.on_event("startup")
def start_line_bundle_load() -> None:
    """ADR-004 opt-in load next to the API (app/services/line_bundle_job.py)."""
    from app.services.line_bundle_job import start_if_configured

    start_if_configured()
