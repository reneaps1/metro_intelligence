"""F4.2 (MI-22) test fixtures.

Uses a disposable, isolated PostgreSQL database (``METRO_TEST_AUTH_DATABASE_URL``,
falling back to a local instance) so these tests never collide with the
migration tests (which read ``METRO_TEST_DATABASE_URL`` and downgrade to base
at the end of each run).

Setup steps (session-scoped, once):
1. Ensure the disposable DB exists.
2. Run Alembic upgrade to head (creates schema + seeds RBAC roles/permissions).
3. Seed one demo user per role (fictitious ``.demo.local`` accounts) so the
   RBAC matrix and abuse tests have identities to authenticate with.

The in-memory auth state (login lockout counter, revoked-jti set) is reset
before every test so cases stay independent.
"""

from __future__ import annotations

import os

import pytest
import sqlalchemy as sa

# The app's engine is pointed at the disposable auth DB by overriding
# app.core.database's engine directly (see below) rather than setting the
# global DATABASE_URL env var -- alembic/env.py resolves DATABASE_URL first,
# so setting it globally would also hijack the migration tests' upgrades.
DEFAULT_AUTH_DB_URL = "postgresql+psycopg://postgres:metro_test_pw@127.0.0.1:5433/metro_test_auth"
AUTH_DB_URL = os.getenv("METRO_TEST_AUTH_DATABASE_URL", DEFAULT_AUTH_DB_URL)

import app.core.database as _db_module  # noqa: E402
from app.core.security import (  # noqa: E402
    _reset_login_attempts_for_tests,
    _reset_revocation_store_for_tests,
    hash_password,
)
from app.models.security import Role, User, UserRole  # noqa: E402

# Override the app's engine/session to target the isolated auth DB. This must
# happen before any fixture or test imports app.core.database symbols that bind
# at call time (get_db looks up SessionLocal as a module global).
_auth_engine = sa.create_engine(AUTH_DB_URL, pool_pre_ping=True)
_db_module.engine = _auth_engine
_db_module.SessionLocal = sa.orm.sessionmaker(bind=_auth_engine, autoflush=False, autocommit=False)

KNOWN_PASSWORD = "TestPassw0rd!2026"

DEMO_USERS = {
    "viewer": "viewer@demo.local",
    "metrologist": "metrologist@demo.local",
    "quality_engineer": "quality.engineer@demo.local",
    "admin": "admin@demo.local",
    "auditor": "auditor@demo.local",
}
DEMO_DISPLAY_NAMES = {
    "viewer": "Demo Viewer",
    "metrologist": "Demo Metrologist",
    "quality_engineer": "Demo Quality Engineer",
    "admin": "Demo Admin",
    "auditor": "Demo Auditor",
}


def _ensure_database() -> None:
    # CREATE DATABASE must run outside any transaction; use psycopg directly
    # with autocommit enabled.
    db_name = AUTH_DB_URL.rsplit("/", 1)[1]
    admin_url = AUTH_DB_URL.replace("+psycopg", "").rsplit("/", 1)[0] + "/postgres"
    import psycopg

    conn = psycopg.connect(admin_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if cur.fetchone() is None:
                cur.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        conn.close()


def _run_alembic(head: str) -> None:
    import pathlib

    import alembic.command
    import alembic.config

    backend_dir = pathlib.Path(__file__).resolve().parents[1]
    cfg = alembic.config.Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    cfg.set_main_option("sqlalchemy.url", AUTH_DB_URL)
    alembic.command.upgrade(cfg, head)


def _seed_demo_users() -> None:
    db = _db_module.SessionLocal()
    try:
        roles = {role.name: role for role in db.execute(sa.select(Role)).scalars()}
        for role_name, email in DEMO_USERS.items():
            if db.execute(sa.text("SELECT 1 FROM security_users WHERE email = :e"), {"e": email}).scalar():
                continue
            user = User(
                email=email,
                display_name=DEMO_DISPLAY_NAMES[role_name],
                password_hash=hash_password(KNOWN_PASSWORD),
                is_active=True,
            )
            db.add(user)
            db.flush()
            db.add(UserRole(user_id=user.id, role_id=roles[role_name].id))
        db.commit()
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def auth_database() -> None:
    _ensure_database()
    _run_alembic("head")
    _seed_demo_users()
    yield
    _run_alembic("base")


@pytest.fixture(autouse=True)
def reset_auth_state() -> None:
    _reset_login_attempts_for_tests()
    _reset_revocation_store_for_tests()
    yield


@pytest.fixture(scope="session")
def auth_app():
    from app.api.v1.auth import router as auth_router
    from app.core.ratelimit import limiter
    from app.core.security import require_permission
    from fastapi import APIRouter, Depends, FastAPI
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    app = FastAPI(title="F4.2 auth test app")

    # One endpoint per seeded permission token, protected by require_permission.
    perm_router = APIRouter()
    engine = sa.create_engine(AUTH_DB_URL)
    with engine.connect() as conn:
        tokens = conn.execute(sa.text("SELECT token FROM security_permissions")).scalars().all()
    for token in tokens:
        resource, _, action = token.rpartition(".")
        path = f"/perm/{resource}/{action}"

        def _endpoint(
            _res: str = resource, _act: str = action, _user=Depends(require_permission(resource, action))
        ):
            return {"resource": _res, "action": _act}

        perm_router.get(
            path,
            name=f"perm_{resource}_{action}".replace(".", "_"),
            include_in_schema=False,
        )(_endpoint)

    app.include_router(perm_router)
    app.include_router(auth_router)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    yield app


@pytest.fixture(scope="session")
def client(auth_app):
    from fastapi.testclient import TestClient

    return TestClient(auth_app)


@pytest.fixture(scope="session")
def role_tokens(client):
    """One login per role, cached for the whole session (avoids tripping the
    /auth/login rate limit across hundreds of matrix cases)."""
    cache: dict[str, str] = {}

    def _get(role: str) -> str:
        if role not in cache:
            response = client.post(
                "/auth/login",
                data={"username": DEMO_USERS[role], "password": KNOWN_PASSWORD},
            )
            assert response.status_code == 200, response.text
            cache[role] = response.json()["access_token"]
        return cache[role]

    return _get


@pytest.fixture
def auth_headers(client):
    """Return a helper that logs in as a given role and yields auth headers."""

    def _login(role: str) -> dict[str, str]:
        response = client.post(
            "/auth/login",
            data={"username": DEMO_USERS[role], "password": KNOWN_PASSWORD},
        )
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _login


@pytest.fixture
def demo_credentials():
    return DEMO_USERS, KNOWN_PASSWORD
