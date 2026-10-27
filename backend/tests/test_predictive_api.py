"""IQ-F7: /api/v1/predictive -- edition gating, RBAC, contracts and validation."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from app.api.v1.auth import router as auth_router
from app.api.v1.predictive import router as predictive_router
from app.core.config import get_settings
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import DEMO_USERS, KNOWN_PASSWORD

BASE = "/api/v1/predictive"
ENDPOINTS = ("model-lab", "nok-waves", "cusum", "what-if", "failure-study")


@pytest.fixture(scope="session")
def client(auth_database: None) -> TestClient:
    app = FastAPI(title="IQ-F7 predictive test app")
    app.include_router(auth_router)
    app.include_router(predictive_router, prefix="/api/v1")
    return TestClient(app)


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


@pytest.fixture(autouse=True)
def industrial(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., None]]:
    settings = get_settings()

    def _set(**values: object) -> None:
        for key, value in values.items():
            monkeypatch.setattr(settings, key, value)

    _set(app_edition="industrial", demo_model_lab_path=None)
    yield _set


def test_metrology_edition_hides_every_endpoint(client: TestClient, as_role, industrial) -> None:
    industrial(app_edition="metrology")
    for path in ENDPOINTS:
        assert client.get(f"{BASE}/{path}", headers=as_role("admin")).status_code == 404, path


def test_rbac(client: TestClient, as_role) -> None:
    for path in ENDPOINTS:
        assert client.get(f"{BASE}/{path}").status_code == 401, path
        assert client.get(f"{BASE}/{path}", headers=as_role("viewer")).status_code == 403, path
        for role in ("metrologist", "quality_engineer", "auditor"):
            assert client.get(f"{BASE}/{path}", headers=as_role(role)).status_code == 200, (path, role)


def test_model_lab_is_the_labelled_placeholder_without_private_file(client: TestClient, as_role) -> None:
    body = client.get(f"{BASE}/model-lab", headers=as_role("quality_engineer")).json()
    assert body["source"] == "placeholder" and body["illustrative"] is True
    assert body["has_threshold_results"] is False
    assert {m["family"] for m in body["models"]} == {"ml_tabular", "deep_learning"}
    assert all(m["fp_per_tp"] is not None for m in body["models"])


def test_nok_waves_contract(client: TestClient, as_role) -> None:
    body = client.get(
        f"{BASE}/nok-waves",
        params={"machine": "INY-01", "window": 5, "threshold": 4},
        headers=as_role("metrologist"),
    ).json()
    assert body["source_type"] == "SIMULATED"
    assert body["engine_version"].endswith("-experimental")
    s = body["summary"]
    assert (s["episodes"], s["anticipated"], s["detected"]) == (3, 0, 3)
    assert s["mean_delay_min"] > 0
    assert any(e["false_alarm"] for e in body["alert_events"])
    assert len(body["hours"]) == 168
    assert all(e["delay_min"] >= 0 for e in body["episodes"])


def test_cusum_contract_and_unknown_series(client: TestClient, as_role) -> None:
    h = as_role("metrologist")
    body = client.get(f"{BASE}/cusum", params={"series": "PinPositionY"}, headers=h).json()
    assert body["drift_detected"] is True and body["drift_direction"] == "upward"
    assert len(body["points"]) == 168 and body["drift_ts"] is not None
    assert client.get(f"{BASE}/cusum", params={"series": "nok_rate"}, headers=h).status_code == 200
    assert client.get(f"{BASE}/cusum", params={"series": "Nope"}, headers=h).status_code == 404


def test_what_if_is_hypothetical_and_validated(client: TestClient, as_role) -> None:
    h = as_role("metrologist")
    body = client.get(f"{BASE}/what-if", params={"mold_delta": 8}, headers=h).json()
    assert body["hypothetical"] is True and body["source_type"] == "SIMULATED"
    assert body["nok_probability"] > body["reference_nok_probability"]
    assert any("ciclo" in note for note in body["not_modelled"])
    for params in ({"hold_pressure": 400}, {"mold_delta": 30}, {"nest": 13}):
        assert client.get(f"{BASE}/what-if", params=params, headers=h).status_code == 422, params


def test_failure_study_contract(client: TestClient, as_role) -> None:
    body = client.get(f"{BASE}/failure-study", headers=as_role("metrologist")).json()
    assert body["engine_version"].endswith("-experimental")
    assert len(body["thresholds"]) == 19
    assert {b["key"] for b in body["baselines"]} == {"last_hour_failure", "constant_rate"}
    assert body["model_pr_auc"] > max(b["pr_auc"] for b in body["baselines"])
    assert body["timeline"]["points"] and body["limitations"]


@pytest.mark.parametrize("params", [{"machine": "INY-09"}, {"window": 0}, {"threshold": 0}, {"horizon": 100}])
def test_nok_waves_validation(client: TestClient, as_role, params: dict) -> None:
    assert client.get(f"{BASE}/nok-waves", params=params, headers=as_role("metrologist")).status_code == 422
