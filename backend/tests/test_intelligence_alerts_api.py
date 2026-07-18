"""Live Monitor alarm fix: `/alerts` and `/alerts/{id}/acknowledge` API
integration tests -- RBAC per rbac.md's `intelligence.alert` row and
acknowledge idempotency. Detection/persistence itself is covered in
``test_alarm_detection_service.py`` and the WS wiring in
``test_live_monitor_api.py``."""

from __future__ import annotations

import uuid

import pytest
from app.api.v1.auth import router as auth_router
from app.api.v1.intelligence import router as intelligence_router
from app.core.database import SessionLocal
from app.models.catalog import Characteristic, CharacteristicClassification, PartNumber, ProductFamily
from app.models.intelligence import Alert
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import DEMO_USERS, KNOWN_PASSWORD


@pytest.fixture(scope="session")
def alerts_app(auth_database: None) -> FastAPI:
    app = FastAPI(title="Live Monitor alarm fix test app")
    app.include_router(auth_router)
    app.include_router(intelligence_router, prefix="/api/v1")
    return app


@pytest.fixture(scope="session")
def alerts_client(alerts_app: FastAPI) -> TestClient:
    return TestClient(alerts_app)


@pytest.fixture(scope="session")
def as_role(alerts_client: TestClient):
    cache: dict[str, dict[str, str]] = {}

    def _login(role: str) -> dict[str, str]:
        if role not in cache:
            response = alerts_client.post(
                "/auth/login",
                data={"username": DEMO_USERS[role], "password": KNOWN_PASSWORD},
            )
            assert response.status_code == 200, response.text
            cache[role] = {"Authorization": f"Bearer {response.json()['access_token']}"}
        return cache[role]

    return _login


@pytest.fixture
def demo_alert() -> dict:
    """A real, persisted, open alert against a real characteristic --
    `trigger_id` doesn't need a real `MeasurementResult` row here (it's a
    bare column, no FK) since this suite exercises the REST layer, not
    detection itself."""
    suffix = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        family = ProductFamily(code=f"MI-DEMO-ALRT-{suffix}", name="Demo family (fictitious)")
        db.add(family)
        db.flush()
        part = PartNumber(product_family_id=family.id, code=f"MI-DEMO-ALRT-{suffix}", name="Demo bracket")
        db.add(part)
        classification = CharacteristicClassification(code=f"ALRT-CLS-{suffix}", name="Demo classification")
        db.add(classification)
        db.flush()
        characteristic = Characteristic(
            part_number_id=part.id,
            balloon_number="1",
            name="Alert API demo diameter",
            characteristic_type="diameter",
            unit="mm",
            classification_id=classification.id,
        )
        db.add(characteristic)
        db.flush()
        alert = Alert(
            severity="warning",
            target_roles=["metrologist", "quality_engineer", "admin"],
            trigger_type="compliance_violation",
            trigger_id=uuid.uuid4(),
            characteristic_id=characteristic.id,
            engine_name="alarm_rules_engine",
            engine_version="v1",
            rationale="0.150 mm above the upper tolerance limit.",
            computed_inputs={"value": "10.15", "deviation": "0.15"},
            message="0.150 mm above the upper tolerance limit.",
        )
        db.add(alert)
        db.commit()
        return {"alert_id": alert.id, "characteristic_id": characteristic.id}
    finally:
        db.close()


def _auth(token_headers: dict[str, str]) -> dict[str, str]:
    return token_headers


# --- GET /alerts RBAC (rbac.md: read = viewer, metrologist,
# quality_engineer, admin, auditor -- every seeded role) -------------------


@pytest.mark.parametrize("role", ["viewer", "metrologist", "quality_engineer", "admin", "auditor"])
def test_list_alerts_allowed_for_every_seeded_role(
    alerts_client: TestClient, as_role, demo_alert: dict, role: str
) -> None:
    response = alerts_client.get("/api/v1/alerts", headers=_auth(as_role(role)))
    assert response.status_code == 200


def test_list_alerts_requires_authentication(alerts_client: TestClient) -> None:
    response = alerts_client.get("/api/v1/alerts")
    assert response.status_code == 401


def test_list_alerts_includes_the_real_persisted_alert(
    alerts_client: TestClient, as_role, demo_alert: dict
) -> None:
    response = alerts_client.get(
        "/api/v1/alerts",
        params={"characteristic_id": str(demo_alert["characteristic_id"])},
        headers=_auth(as_role("metrologist")),
    )
    assert response.status_code == 200
    body = response.json()
    ids = [item["id"] for item in body["items"]]
    assert str(demo_alert["alert_id"]) in ids
    match = next(item for item in body["items"] if item["id"] == str(demo_alert["alert_id"]))
    assert match["trigger_type"] == "compliance_violation"
    assert match["rationale"] == "0.150 mm above the upper tolerance limit."
    assert match["computed_inputs"] == {"value": "10.15", "deviation": "0.15"}
    assert match["acknowledged_at"] is None


def test_list_alerts_filters_by_open_state(alerts_client: TestClient, as_role, demo_alert: dict) -> None:
    response = alerts_client.get(
        "/api/v1/alerts",
        params={"characteristic_id": str(demo_alert["characteristic_id"]), "state": "open"},
        headers=_auth(as_role("metrologist")),
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1

    response = alerts_client.get(
        "/api/v1/alerts",
        params={"characteristic_id": str(demo_alert["characteristic_id"]), "state": "acknowledged"},
        headers=_auth(as_role("metrologist")),
    )
    assert response.status_code == 200
    assert response.json()["items"] == []


# --- POST /alerts/{id}/acknowledge RBAC (rbac.md: update = viewer,
# metrologist, quality_engineer, admin -- every seeded role except auditor)
# -----------------------------------------------------------------------


@pytest.mark.parametrize("role", ["viewer", "metrologist", "quality_engineer", "admin"])
def test_acknowledge_allowed_for_every_update_role(
    alerts_client: TestClient, as_role, demo_alert: dict, role: str
) -> None:
    response = alerts_client.post(
        f"/api/v1/alerts/{demo_alert['alert_id']}/acknowledge", headers=_auth(as_role(role))
    )
    assert response.status_code == 200
    body = response.json()
    assert body["acknowledged_at"] is not None
    assert body["acknowledged_by_user_id"] is not None


def test_acknowledge_denied_for_auditor(alerts_client: TestClient, as_role, demo_alert: dict) -> None:
    response = alerts_client.post(
        f"/api/v1/alerts/{demo_alert['alert_id']}/acknowledge", headers=_auth(as_role("auditor"))
    )
    assert response.status_code == 403


def test_acknowledge_is_not_idempotent_a_second_call_fails_cleanly(
    alerts_client: TestClient, as_role, demo_alert: dict
) -> None:
    first = alerts_client.post(
        f"/api/v1/alerts/{demo_alert['alert_id']}/acknowledge", headers=_auth(as_role("metrologist"))
    )
    assert first.status_code == 200

    second = alerts_client.post(
        f"/api/v1/alerts/{demo_alert['alert_id']}/acknowledge", headers=_auth(as_role("metrologist"))
    )
    assert second.status_code == 409


def test_acknowledge_unknown_alert_returns_404(alerts_client: TestClient, as_role) -> None:
    response = alerts_client.post(
        f"/api/v1/alerts/{uuid.uuid4()}/acknowledge", headers=_auth(as_role("metrologist"))
    )
    assert response.status_code == 404
