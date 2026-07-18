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

import time
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
from app.models.intelligence import Alert
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


def _build_characteristic(
    values: tuple[str, ...], *, lower_tol: Decimal | int = -1, upper_tol: Decimal | int = 1
) -> dict:
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
            characteristic_id=characteristic.id,
            nominal=10,
            lower_tol=lower_tol,
            upper_tol=upper_tol,
            unit="mm",
        )
        db.add(spec)
        db.flush()
        program = MeasurementProgram(
            part_number_id=part.id, name="LM CMM Program", output_mapping={"1": "COL_1"}
        )
        db.add(program)
        db.flush()

        start = datetime(2026, 1, 1, tzinfo=UTC)
        for i, raw_value in enumerate(values):
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
                    value=Decimal(raw_value),
                )
            )
        db.commit()
        return {"characteristic_id": characteristic.id, "point_count": len(values)}
    finally:
        db.close()


@pytest.fixture
def demo_characteristic() -> dict:
    """A characteristic with an active spec and a short, deterministic
    measurement history spread one day apart -- enough to exercise a full
    replay (including at least one control-limits recalculation) quickly."""
    return _build_characteristic(("10.0", "10.1", "9.9", "10.2", "9.8", "10.0"))


@pytest.fixture
def demo_characteristic_with_nok() -> dict:
    """Live Monitor alarm fix: a tight tolerance with exactly one point
    (the last of 5, aligned with `CONTROL_LIMIT_RECALC_EVERY`) clearly
    outside it -- deterministically triggers exactly one
    `compliance_violation` alarm."""
    return _build_characteristic(
        ("10.00", "10.01", "9.99", "10.02", "11.00"), lower_tol=Decimal("-0.05"), upper_tol=Decimal("0.05")
    )


@pytest.fixture
def demo_characteristic_with_consecutive_nok() -> dict:
    """Live Monitor alarm fix: two consecutive out-of-tolerance points --
    proves the dedup rule (one open alert per characteristic + rule), not
    just that an alarm can fire once."""
    return _build_characteristic(
        ("10.00", "10.01", "11.00", "11.20", "9.99"), lower_tol=Decimal("-0.05"), upper_tol=Decimal("0.05")
    )


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


def _ws_url(
    token: str,
    characteristic_ids: str,
    *,
    instant: bool = False,
    seconds_per_replay_day: float | None = None,
) -> str:
    url = f"/api/v1/ws/live-monitor?token={token}&characteristic_ids={characteristic_ids}"
    if instant:
        url += "&seconds_per_replay_day=0"
    elif seconds_per_replay_day is not None:
        url += f"&seconds_per_replay_day={seconds_per_replay_day}"
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


# --- LM.3: presenter controls ------------------------------------------------
# Pause/resume's actual timing behavior (does it really stop advancing, does
# a speed change take effect without a restart) is unit-tested against
# `PlaybackControl` directly in test_live_replay_playback_control.py -- these
# integration tests cover the WS wiring: a control message reaches the right
# session, and RBAC gates who it's allowed to affect.


def test_ws_pause_then_resume_preserves_every_point_with_no_loss_or_duplication(
    client: TestClient, as_role, demo_characteristic: dict
) -> None:
    characteristic_id = str(demo_characteristic["characteristic_id"])
    # A small but nonzero pace (unlike the `instant=True` tests above, where
    # every wait is skipped and there would be nothing for a pause to gate).
    url = _ws_url(as_role("quality_engineer"), characteristic_id, seconds_per_replay_day=0.05)

    with client.websocket_connect(url) as websocket:
        first = websocket.receive_json()
        assert first["type"] == "point"

        websocket.send_json({"type": "control", "action": "pause"})
        time.sleep(0.3)
        websocket.send_json({"type": "control", "action": "resume"})

        rest = _collect_all(websocket)

    points = [first] + [m for m in rest if m["type"] == "point"]
    assert len(points) == demo_characteristic["point_count"]
    measured_ats = [p["measured_at"] for p in points]
    assert len(measured_ats) == len(set(measured_ats)), "no point was re-emitted"
    assert measured_ats == sorted(measured_ats), "no point was skipped out of order"


def test_ws_control_message_from_a_role_without_update_permission_is_ignored(
    client: TestClient, as_role, demo_characteristic: dict
) -> None:
    # `metrologist` has `live_monitor.stream` (can watch) but not
    # `live_monitor.update` (migration 0007) -- its pause attempt must not
    # actually pause the session, or this test would hang waiting for a
    # close that pausing-forever would never send.
    characteristic_id = str(demo_characteristic["characteristic_id"])
    url = _ws_url(as_role("metrologist"), characteristic_id, seconds_per_replay_day=0.05)

    with client.websocket_connect(url) as websocket:
        websocket.send_json({"type": "control", "action": "pause"})
        messages = _collect_all(websocket)

    point_messages = [m for m in messages if m["type"] == "point"]
    assert len(point_messages) == demo_characteristic["point_count"]


# --- LM.3: scenario candidates ------------------------------------------------


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_scenario_candidates_requires_authentication(client: TestClient) -> None:
    response = client.get(
        "/api/v1/characteristics/scenario-candidates", params={"scenario": "stable_capable"}
    )
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["viewer", "metrologist", "auditor"])
def test_scenario_candidates_denied_without_update_permission(client: TestClient, as_role, role: str) -> None:
    response = client.get(
        "/api/v1/characteristics/scenario-candidates",
        params={"scenario": "stable_capable"},
        headers=_auth_header(as_role(role)),
    )
    assert response.status_code == 403


@pytest.mark.parametrize("role", ["quality_engineer", "admin"])
def test_scenario_candidates_allowed_with_update_permission(client: TestClient, as_role, role: str) -> None:
    response = client.get(
        "/api/v1/characteristics/scenario-candidates",
        params={"scenario": "stable_capable"},
        headers=_auth_header(as_role(role)),
    )
    assert response.status_code == 200


def test_scenario_candidates_rejects_an_unknown_scenario_name(client: TestClient, as_role) -> None:
    response = client.get(
        "/api/v1/characteristics/scenario-candidates",
        params={"scenario": "not_a_real_scenario"},
        headers=_auth_header(as_role("admin")),
    )
    assert response.status_code == 422


def test_scenario_candidates_returns_a_bounded_list_of_real_ids(
    client: TestClient, as_role, demo_characteristic: dict
) -> None:
    response = client.get(
        "/api/v1/characteristics/scenario-candidates",
        params={"scenario": "stable_capable", "limit": 3},
        headers=_auth_header(as_role("admin")),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scenario"] == "stable_capable"
    assert len(body["characteristic_ids"]) <= 3
    assert body["candidate_pool_size"] >= 1  # at least the fixture characteristic
    for characteristic_id in body["characteristic_ids"]:
        uuid.UUID(characteristic_id)  # every id is a real, well-formed UUID


# --- Live Monitor alarm fix: alert_created WS event + persistence ----------


def _alert_count(characteristic_id: uuid.UUID, trigger_type: str) -> int:
    db = SessionLocal()
    try:
        return db.execute(
            sa.select(sa.func.count())
            .select_from(Alert)
            .where(Alert.characteristic_id == characteristic_id, Alert.trigger_type == trigger_type)
        ).scalar_one()
    finally:
        db.close()


def test_ws_emits_alert_created_and_persists_it_for_a_nok_point(
    client: TestClient, as_role, demo_characteristic_with_nok: dict
) -> None:
    characteristic_id = str(demo_characteristic_with_nok["characteristic_id"])
    url = _ws_url(as_role("metrologist"), characteristic_id, instant=True)

    with client.websocket_connect(url) as websocket:
        messages = _collect_all(websocket)

    alert_messages = [m for m in messages if m["type"] == "alert_created"]
    compliance_alerts = [m for m in alert_messages if m["trigger_type"] == "compliance_violation"]
    assert len(compliance_alerts) == 1
    assert compliance_alerts[0]["characteristic_id"] == characteristic_id
    assert compliance_alerts[0]["severity"] == "warning"
    assert compliance_alerts[0]["engine_name"] == "alarm_rules_engine"
    uuid.UUID(compliance_alerts[0]["id"])  # a real persisted row id, not a placeholder

    assert _alert_count(demo_characteristic_with_nok["characteristic_id"], "compliance_violation") == 1


def test_ws_does_not_duplicate_alerts_for_consecutive_nok_points(
    client: TestClient, as_role, demo_characteristic_with_consecutive_nok: dict
) -> None:
    characteristic_id = demo_characteristic_with_consecutive_nok["characteristic_id"]
    url = _ws_url(as_role("metrologist"), str(characteristic_id), instant=True)

    with client.websocket_connect(url) as websocket:
        messages = _collect_all(websocket)

    point_messages = [m for m in messages if m["type"] == "point"]
    nok_points = [m for m in point_messages if not m["is_ok"]]
    assert len(nok_points) == 2  # both out-of-tolerance points really are NOK

    alert_messages = [m for m in messages if m["type"] == "alert_created"]
    compliance_alerts = [m for m in alert_messages if m["trigger_type"] == "compliance_violation"]
    assert len(compliance_alerts) == 1  # only the first NOK point opened an alert -- dedup blocked the second

    assert _alert_count(characteristic_id, "compliance_violation") == 1


def test_ws_never_alarms_a_fully_capable_stable_characteristic(
    client: TestClient, as_role, demo_characteristic: dict
) -> None:
    # Regression guard for the two tests above: a characteristic with no NOK
    # points and comfortable tolerance (the original LM.1 fixture) must not
    # emit any alert at all.
    characteristic_id = str(demo_characteristic["characteristic_id"])
    url = _ws_url(as_role("metrologist"), characteristic_id, instant=True)

    with client.websocket_connect(url) as websocket:
        messages = _collect_all(websocket)

    assert [m for m in messages if m["type"] == "alert_created"] == []
