"""F4.1 (MI-21) acceptance criterion: an internal error must produce a
generic response with no internals leaked (CLAUDE.md §18.5). Uses a
throwaway FastAPI app rather than adding a debug-only route to the real
`app.main:app` (that would be dead/test-only code in production)."""
from __future__ import annotations

from app.core.errors import register_exception_handlers
from fastapi import FastAPI
from fastapi.testclient import TestClient

SECRET_DETAIL = "password=hunter2 at /etc/metro/secrets.env"


def _client_with_a_route_that_blows_up() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError(SECRET_DETAIL)

    return TestClient(app, raise_server_exceptions=False)


def test_unhandled_exception_returns_a_sanitized_generic_body() -> None:
    client = _client_with_a_route_that_blows_up()
    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}


def test_unhandled_exception_response_leaks_no_internals() -> None:
    client = _client_with_a_route_that_blows_up()
    response = client.get("/boom")

    body = response.text
    assert SECRET_DETAIL not in body
    assert "RuntimeError" not in body
    assert "Traceback" not in body
    assert "boom" not in body
