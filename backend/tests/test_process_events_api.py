"""F4.7 (MI-27): process events API integration tests.

Acceptance criteria (Notion MI-27):
- CRUD funcional con RBAC y auditoría (create + read; no update/delete in
  scope -- events are append-only).
- Filtro por ventana temporal correcto.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from app.api.v1.auth import router as auth_router
from app.api.v1.process_events import router as process_events_router
from app.core.database import SessionLocal
from app.models.security import AuditLog
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import DEMO_USERS, KNOWN_PASSWORD


@pytest.fixture(scope="session")
def events_app(auth_database: None) -> FastAPI:
    app = FastAPI(title="F4.7 process events test app")
    app.include_router(auth_router)
    app.include_router(process_events_router, prefix="/api/v1")
    return app


@pytest.fixture(scope="session")
def client(events_app: FastAPI) -> TestClient:
    return TestClient(events_app)


@pytest.fixture(scope="session")
def as_role(client: TestClient):
    cache: dict[str, dict[str, str]] = {}

    def _login(role: str) -> dict[str, str]:
        if role not in cache:
            response = client.post(
                "/auth/login",
                data={"username": DEMO_USERS[role], "password": KNOWN_PASSWORD},
            )
            assert response.status_code == 200, response.text
            cache[role] = {"Authorization": f"Bearer {response.json()['access_token']}"}
        return cache[role]

    return _login


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def test_unauthenticated_requests_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/process-events").status_code == 401


def test_viewer_cannot_read(client: TestClient, as_role) -> None:
    response = client.get("/api/v1/process-events", headers=as_role("viewer"))
    assert response.status_code == 403


def test_viewer_cannot_create(client: TestClient, as_role) -> None:
    response = client.post(
        "/api/v1/process-events",
        headers=as_role("viewer"),
        json={
            "event_type": "tool_change",
            "occurred_at": _iso(datetime.now(UTC)),
            "description": "Should be denied.",
        },
    )
    assert response.status_code == 403


def test_auditor_can_read_but_not_create(client: TestClient, as_role) -> None:
    assert client.get("/api/v1/process-events", headers=as_role("auditor")).status_code == 200
    response = client.post(
        "/api/v1/process-events",
        headers=as_role("auditor"),
        json={
            "event_type": "tool_change",
            "occurred_at": _iso(datetime.now(UTC)),
            "description": "Should be denied for auditor.",
        },
    )
    assert response.status_code == 403


def test_metrologist_can_create_and_it_is_audited(client: TestClient, as_role) -> None:
    headers = as_role("metrologist")
    description = f"Tool change during demo test {uuid.uuid4().hex[:8]}"
    response = client.post(
        "/api/v1/process-events",
        headers=headers,
        json={
            "event_type": "tool_change",
            "occurred_at": _iso(datetime.now(UTC)),
            "description": description,
            "event_metadata": {"tool_id": "T-42"},
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["description"] == description
    assert body["event_metadata"] == {"tool_id": "T-42"}

    event_id = uuid.UUID(body["id"])
    db = SessionLocal()
    try:
        actions = (
            db.execute(
                sa.select(AuditLog.action).where(
                    AuditLog.entity_type == "context.process_event", AuditLog.entity_id == event_id
                )
            )
            .scalars()
            .all()
        )
    finally:
        db.close()
    assert "created" in actions


def test_metadata_over_size_limit_rejected(client: TestClient, as_role) -> None:
    response = client.post(
        "/api/v1/process-events",
        headers=as_role("metrologist"),
        json={
            "event_type": "maintenance",
            "occurred_at": _iso(datetime.now(UTC)),
            "description": "Oversized metadata test.",
            "event_metadata": {"blob": "x" * 9000},
        },
    )
    assert response.status_code == 422


def test_event_type_filter(client: TestClient, as_role) -> None:
    headers = as_role("metrologist")
    marker = uuid.uuid4().hex[:8]
    for event_type in ("tool_change", "maintenance"):
        client.post(
            "/api/v1/process-events",
            headers=headers,
            json={
                "event_type": event_type,
                "occurred_at": _iso(datetime.now(UTC)),
                "description": f"{event_type}-{marker}",
            },
        )

    response = client.get(
        "/api/v1/process-events",
        headers=headers,
        params={"event_type": "maintenance", "page_size": 200},
    )
    assert response.status_code == 200
    descriptions = {item["description"] for item in response.json()["items"]}
    assert f"maintenance-{marker}" in descriptions
    assert f"tool_change-{marker}" not in descriptions


def test_time_window_filter(client: TestClient, as_role) -> None:
    headers = as_role("metrologist")
    marker = uuid.uuid4().hex[:8]
    now = datetime.now(UTC)
    old_event_at = now - timedelta(days=30)
    recent_event_at = now - timedelta(hours=1)

    client.post(
        "/api/v1/process-events",
        headers=headers,
        json={
            "event_type": "machine_adjustment",
            "occurred_at": _iso(old_event_at),
            "description": f"old-{marker}",
        },
    )
    client.post(
        "/api/v1/process-events",
        headers=headers,
        json={
            "event_type": "machine_adjustment",
            "occurred_at": _iso(recent_event_at),
            "description": f"recent-{marker}",
        },
    )

    response = client.get(
        "/api/v1/process-events",
        headers=headers,
        params={
            "occurred_from": _iso(now - timedelta(days=1)),
            "occurred_to": _iso(now),
            "page_size": 200,
        },
    )
    assert response.status_code == 200
    descriptions = {item["description"] for item in response.json()["items"]}
    assert f"recent-{marker}" in descriptions
    assert f"old-{marker}" not in descriptions
