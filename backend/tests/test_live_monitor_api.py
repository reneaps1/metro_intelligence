"""LM.1 (docs/tasks/LM1-live-monitor-mvp.md): Live Monitor WebSocket
integration tests against a real Postgres instance.

Acceptance criteria covered here (unit-level determinism of the event
builder itself lives in ``test_live_replay_service.py``):
- The WS rejects connections without a valid token or without the
  ``live_monitor.stream`` permission (connection closed with
  ``WS_1008_POLICY_VIOLATION`` -- there is no HTTP status code to check on a
  WebSocket handshake, so the close code is the RBAC assertion here).
- No replayed point is ever inserted into ``measurement_results`` (row count
  before/after a full replay is identical).
- The same characteristic replayed twice over the wire produces the same
  event sequence (speed cranked up so both connections finish fast).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import sqlalchemy as sa
from app.api.v1.auth import router as auth_router
from app.api.v1.live_monitor import router as live_monitor_router
from app.core.database import SessionLocal
from app.models.catalog import (
    Characteristic,
    CharacteristicClassification,
    MeasurementProgram,
    PartNumber,
    ProductFamily,
    Specification,
)
from app.models.measurement import MeasurementResult, MeasurementRun, MeasurementSample
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from conftest import DEMO_USERS, KNOWN_PASSWORD


@pytest.fixture(scope="session")
def live_monitor_app(auth_database: None) -> FastAPI:
    app = FastAPI(title="LM.1 live monitor test app")
    app.include_router(auth_router)
    app.include_router(live_monitor_router, prefix="/api/v1")
    return app


@pytest.fixture(scope="session")
def client(live_monitor_app: FastAPI) -> TestClient:
    return TestClient(live_monitor_app)


@pytest.fixture(scope="session")
def as_role(client: TestClient):
    cache: dict[str, str] = {}

    def _token(role: str) -> str:
        if role not in cache:
            response = client.post(
                "/auth/login",
                data={"username": DEMO_USERS[role], "password": KNOWN_PASSWORD},
            )
            assert response.status_code == 200, response.text
            cache[role] = response.json()["access_token"]
        return cache[role]

    return _token


@pytest.fixture
def demo_characteristic() -> dict:
    """A characteristic with an active spec and a short, deterministic
    measurement history spread one day apart -- enough to exercise a full
    replay (including at least one control-limits recalculation) quickly."""
    suffix = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        family = ProductFamily(code=f"MI-DEMO-LM-{suffix}", name="Demo family (fictitious)")
        db.add(family)
        db.flush()
        part = PartNumber(product_family_id=family.id, code=f"MI-DEMO-LM-{suffix}", name="Demo bracket")
        db.add(part)
        classification = CharacteristicClassification(code=f"LM-CLS-{suffix}", name="Demo classification")
        db.add(classification)
        db.flush()
        characteristic = Characteristic(
            part_number_id=part.id,
            balloon_number="1",
            name="Live monitor demo diameter",
            characteristic_type="diameter",
            unit="mm",
            classification_id=classification.id,
        )
        db.add(characteristic)
        db.flush()
        spec = Specification(
            characteristic_id=characteristic.id, nominal=10, lower_tol=-1, upper_tol=1, unit="mm"
        )
        db.add(spec)
        db.flush()
        program = MeasurementProgram(
            part_number_id=part.id, name="LM CMM Program", output_mapping={"1": "COL_1"}
        )
        db.add(program)
        db.flush()

        start = datetime(2026, 1, 1, tzinfo=UTC)
        values = [Decimal(v) for v in ("10.0", "10.1", "9.9", "10.2", "9.8", "10.0")]
        for i, value in enumerate(values):
            run = MeasurementRun(
                measurement_program_id=program.id,
                operator_identifier="OP",
                run_at=start + timedelta(days=i),
            )
            db.add(run)
            db.flush()
            sample = MeasurementSample(measurement_run_id=run.id, sample_sequence=1)
            db.add(sample)
            db.flush()
            db.add(
                MeasurementResult(
                    measured_at=run.run_at,
                    measurement_sample_id=sample.id,
                    characteristic_id=characteristic.id,
                    specification_id=spec.id,
                    value=value,
                )
            )
        db.commit()
        return {"characteristic_id": characteristic.id, "point_count": len(values)}
    finally:
        db.close()


def _measurement_result_count() -> int:
    db = SessionLocal()
    try:
        return db.execute(sa.select(sa.func.count()).select_from(MeasurementResult)).scalar_one()
    finally:
        db.close()


def _collect_all(websocket) -> list[dict]:
    """The server closes the socket once every requested characteristic's
    replay is exhausted -- keep reading until that close arrives."""
    messages: list[dict] = []
    try:
        while True:
            messages.append(websocket.receive_json())
    except WebSocketDisconnect:
        pass
    return messages


def _ws_url(token: str, characteristic_ids: str, *, instant: bool = False) -> str:
    url = f"/api/v1/ws/live-monitor?token={token}&characteristic_ids={characteristic_ids}"
    if instant:
        url += "&seconds_per_replay_day=0"
    return url


def test_ws_rejects_invalid_token(client: TestClient, demo_characteristic: dict) -> None:
    url = _ws_url("not-a-real-token", str(demo_characteristic["characteristic_id"]))
    with pytest.raises(WebSocketDisconnect) as exc_info, client.websocket_connect(url):
        pass
    assert exc_info.value.code == 1008


def test_ws_rejects_role_without_stream_permission(
    client: TestClient, as_role, demo_characteristic: dict
) -> None:
    # `viewer` is not in the granted-roles list for `live_monitor.stream`
    # (migration 0006) -- same denial this role gets on any RBAC-protected
    # REST endpoint it lacks a permission for.
    url = _ws_url(as_role("viewer"), str(demo_characteristic["characteristic_id"]))
    with pytest.raises(WebSocketDisconnect) as exc_info, client.websocket_connect(url):
        pass
    assert exc_info.value.code == 1008


def test_ws_rejects_missing_characteristic_ids(client: TestClient, as_role) -> None:
    url = _ws_url(as_role("metrologist"), "")
    with pytest.raises(WebSocketDisconnect) as exc_info, client.websocket_connect(url):
        pass
    assert exc_info.value.code == 1008


def test_ws_streams_points_and_control_limits_for_a_granted_role(
    client: TestClient, as_role, demo_characteristic: dict
) -> None:
    characteristic_id = str(demo_characteristic["characteristic_id"])
    url = _ws_url(as_role("metrologist"), characteristic_id, instant=True)

    with client.websocket_connect(url) as websocket:
        messages = _collect_all(websocket)

    point_messages = [m for m in messages if m["type"] == "point"]
    control_messages = [m for m in messages if m["type"] == "control_limits_updated"]

    assert len(point_messages) == demo_characteristic["point_count"]
    assert all(m["characteristic_id"] == characteristic_id for m in messages)
    assert len(control_messages) >= 1
    assert control_messages[0]["engine_name"] == "spc_engine"
    # Time-ordered, matching the seeded sequence.
    measured_ats = [m["measured_at"] for m in point_messages]
    assert measured_ats == sorted(measured_ats)


def test_replay_never_inserts_measurement_results(
    client: TestClient, as_role, demo_characteristic: dict
) -> None:
    characteristic_id = str(demo_characteristic["characteristic_id"])
    url = _ws_url(as_role("quality_engineer"), characteristic_id, instant=True)

    before = _measurement_result_count()
    with client.websocket_connect(url) as websocket:
        _collect_all(websocket)
    after = _measurement_result_count()

    assert after == before


def test_replaying_the_same_characteristic_twice_yields_the_same_sequence(
    client: TestClient, as_role, demo_characteristic: dict
) -> None:
    characteristic_id = str(demo_characteristic["characteristic_id"])
    url = _ws_url(as_role("admin"), characteristic_id, instant=True)

    with client.websocket_connect(url) as websocket:
        first_run = _collect_all(websocket)
    with client.websocket_connect(url) as websocket:
        second_run = _collect_all(websocket)

    assert first_run == second_run
