from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_response_carries_a_request_id() -> None:
    response = client.get("/health")
    assert response.headers["X-Request-ID"]


def test_api_v1_router_has_the_right_prefix() -> None:
    from app.api.v1.router import api_router

    assert api_router.prefix == "/api/v1"
