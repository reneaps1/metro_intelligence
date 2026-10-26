"""IQ-F1/F2: edition gating, /meta and the simulated industrial-signals API."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime

import pytest
from app.api.v1.auth import router as auth_router
from app.api.v1.industrial_signals import router as industrial_signals_router
from app.api.v1.meta import router as meta_router
from app.core.config import get_settings
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import DEMO_USERS, KNOWN_PASSWORD

SID = "L1.INY-01.injection_pressure"


@pytest.fixture(scope="session")
def signals_app(auth_database: None) -> FastAPI:
    app = FastAPI(title="IQ-F2 industrial signals test app")
    app.include_router(auth_router)
    app.include_router(meta_router, prefix="/api/v1")
    app.include_router(industrial_signals_router, prefix="/api/v1")
    return app


@pytest.fixture(scope="session")
def client(signals_app: FastAPI) -> TestClient:
    return TestClient(signals_app)


@pytest.fixture(scope="session")
def as_role(client: TestClient):
    cache: dict[str, dict[str, str]] = {}

    def _login(role: str) -> dict[str, str]:
        if role not in cache:
            response = client.post(
                "/auth/login", data={"username": DEMO_USERS[role], "password": KNOWN_PASSWORD}
            )
            assert response.status_code == 200, response.text
            cache[role] = {"Authorization": f"Bearer {response.json()['access_token']}"}
        return cache[role]

    return _login


@pytest.fixture
def edition(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., None]]:
    settings = get_settings()

    def _set(value: str, label: str = "Cliente demo") -> None:
        monkeypatch.setattr(settings, "app_edition", value)
        monkeypatch.setattr(settings, "demo_client_label", label)

    yield _set


# --- /meta --------------------------------------------------------------------------


def test_meta_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/meta").status_code == 401


def test_meta_metrology_hides_modules_and_client(client: TestClient, as_role, edition) -> None:
    edition("metrology", "Secret Customer")
    body = client.get("/api/v1/meta", headers=as_role("viewer")).json()
    assert body == {"edition": "metrology", "client_label": None, "modules": []}


def test_meta_industrial_exposes_modules_and_label(client: TestClient, as_role, edition) -> None:
    edition("industrial", "Cliente X")
    body = client.get("/api/v1/meta", headers=as_role("viewer")).json()
    assert body["edition"] == "industrial"
    assert body["client_label"] == "Cliente X"
    assert "industrial_signals" in body["modules"]


def test_default_edition_is_metrology() -> None:
    from app.core.config import Settings

    assert Settings.model_fields["app_edition"].default == "metrology"


# --- edition gating ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/industrial-signals/tree",
        "/api/v1/industrial-signals/scenarios",
        f"/api/v1/industrial-signals/series?scenario=normal&signals={SID}",
        "/api/v1/industrial-signals/events?scenario=normal",
    ],
)
def test_metrology_edition_returns_404(client: TestClient, as_role, edition, path: str) -> None:
    edition("metrology")
    assert client.get(path, headers=as_role("admin")).status_code == 404


# --- RBAC ---------------------------------------------------------------------------------


def test_unauthenticated_rejected(client: TestClient, edition) -> None:
    edition("industrial")
    assert client.get("/api/v1/industrial-signals/tree").status_code == 401


def test_viewer_lacks_stream_permission(client: TestClient, as_role, edition) -> None:
    edition("industrial")
    assert client.get("/api/v1/industrial-signals/tree", headers=as_role("viewer")).status_code == 403


@pytest.mark.parametrize("role", ["metrologist", "quality_engineer", "admin", "auditor"])
def test_stream_roles_can_read(client: TestClient, as_role, edition, role: str) -> None:
    edition("industrial")
    assert client.get("/api/v1/industrial-signals/scenarios", headers=as_role(role)).status_code == 200


# --- payloads --------------------------------------------------------------------------------


def test_tree_payload(client: TestClient, as_role, edition) -> None:
    edition("industrial")
    body = client.get("/api/v1/industrial-signals/tree", headers=as_role("metrologist")).json()
    assert body["source_type"] == "SIMULATED"
    assert body["root"]["node_type"] == "plant"


def test_scenarios_payload(client: TestClient, as_role, edition) -> None:
    edition("industrial")
    body = client.get("/api/v1/industrial-signals/scenarios", headers=as_role("metrologist")).json()
    ids = [s["id"] for s in body["items"]]
    assert ids == ["normal", "thermal_drift", "pressure_setpoint_change", "intermittent_fault_cavity_change"]
    assert all(s["event_count"] >= 1 for s in body["items"])


def test_series_payload_and_window(client: TestClient, as_role, edition) -> None:
    edition("industrial")
    response = client.get(
        "/api/v1/industrial-signals/series",
        params={
            "scenario": "normal",
            "signals": f"{SID},L1.INY-01.mold_temp",
            "start": "2026-10-20T07:00:00Z",
            "end": "2026-10-20T07:01:00Z",
            "max_points": 500,
        },
        headers=as_role("metrologist"),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source_type"] == "SIMULATED"
    assert [s["signal_id"] for s in body["series"]] == [SID, "L1.INY-01.mold_temp"]
    pressure = body["series"][0]
    assert pressure["unit"] == "bar"
    assert 0 < pressure["returned_points"] <= 500
    start_ms = int(datetime(2026, 10, 20, 7, 0, tzinfo=UTC).timestamp() * 1000)
    assert all(start_ms <= t <= start_ms + 60_000 for t, _ in pressure["points"])


def test_series_is_deterministic_over_http(client: TestClient, as_role, edition) -> None:
    edition("industrial")
    params = {"scenario": "thermal_drift", "signals": "L1.INY-01.mold_temp", "max_points": 200}
    first = client.get("/api/v1/industrial-signals/series", params=params, headers=as_role("admin")).json()
    second = client.get("/api/v1/industrial-signals/series", params=params, headers=as_role("admin")).json()
    assert first == second


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"scenario": "nope", "signals": SID}, 404),
        ({"scenario": "normal", "signals": "L1.INY-01.nope"}, 404),
        ({"scenario": "normal", "signals": " , "}, 422),
        (
            {
                "scenario": "normal",
                "signals": ",".join(
                    [
                        SID.replace("injection_pressure", k)
                        for k in (
                            "barrel_temp",
                            "mold_temp",
                            "injection_pressure",
                            "holding_pressure",
                            "injection_speed",
                            "screw_position",
                            "cooling_time",
                            "cycle_time",
                            "motor_current",
                            "vibration",
                            "active_cavity",
                            "shot_counter",
                            "alarm",
                        )
                    ]
                ),
            },
            422,
        ),
        ({"scenario": "normal", "signals": SID, "max_points": 10}, 422),
        (
            {
                "scenario": "normal",
                "signals": SID,
                "start": "2026-10-20T08:00:00Z",
                "end": "2026-10-20T07:00:00Z",
            },
            422,
        ),
        ({"scenario": "normal", "signals": SID, "start": "2027-01-01T00:00:00Z"}, 422),
        ({"scenario": "normal", "signals": SID, "start": "2026-10-20T07:00:00"}, 422),
    ],
)
def test_series_validation(client: TestClient, as_role, edition, params: dict, expected: int) -> None:
    edition("industrial")
    response = client.get("/api/v1/industrial-signals/series", params=params, headers=as_role("admin"))
    assert response.status_code == expected, response.text


def test_events_payload_and_filter(client: TestClient, as_role, edition) -> None:
    edition("industrial")
    all_events = client.get(
        "/api/v1/industrial-signals/events", params={"scenario": "thermal_drift"}, headers=as_role("admin")
    ).json()
    assert all_events["source_type"] == "SIMULATED"
    types = {e["event_type"] for e in all_events["items"]}
    assert {"thermal_instability", "alarm", "batch_change"} <= types
    alarm = next(e for e in all_events["items"] if e["event_type"] == "alarm")
    assert alarm["end"] is not None and "L1.INY-01.mold_temp" in alarm["signal_ids"]

    early = client.get(
        "/api/v1/industrial-signals/events",
        params={"scenario": "thermal_drift", "end": "2026-10-20T08:30:00Z"},
        headers=as_role("admin"),
    ).json()
    assert [e["event_type"] for e in early["items"]] == ["batch_change"]
