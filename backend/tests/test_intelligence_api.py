"""F4.8 (MI-28): recommendations/decisions API integration tests.

CLAUDE.md §24 is what this suite is actually protecting: a recommendation
must never have operational effect without an explicit, recorded human
decision. The frequency end-to-end test and the state-machine tests are the
core of that; RBAC and the DB-trigger-immutability test are defense in
depth around it.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from app.api.v1.auth import router as auth_router
from app.api.v1.intelligence import router as intelligence_router
from app.core.database import SessionLocal
from app.models.catalog import (
    Characteristic,
    CharacteristicClassification,
    InspectionFrequency,
    InspectionPlan,
    PartNumber,
    ProductFamily,
    Specification,
)
from app.models.intelligence import Recommendation, RiskAssessment
from app.models.security import AuditLog
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import DEMO_USERS, KNOWN_PASSWORD


@pytest.fixture(scope="session")
def intelligence_app(auth_database: None) -> FastAPI:
    app = FastAPI(title="F4.8 intelligence test app")
    app.include_router(auth_router)
    app.include_router(intelligence_router, prefix="/api/v1")
    return app


@pytest.fixture(scope="session")
def intelligence_client(intelligence_app: FastAPI) -> TestClient:
    return TestClient(intelligence_app)


@pytest.fixture(scope="session")
def as_role(intelligence_client: TestClient):
    cache: dict[str, dict[str, str]] = {}

    def _login(role: str) -> dict[str, str]:
        if role not in cache:
            response = intelligence_client.post(
                "/auth/login",
                data={"username": DEMO_USERS[role], "password": KNOWN_PASSWORD},
            )
            assert response.status_code == 200, response.text
            cache[role] = {"Authorization": f"Bearer {response.json()['access_token']}"}
        return cache[role]

    return _login


def _make_catalog(db) -> dict:
    suffix = uuid.uuid4().hex[:8]
    family = ProductFamily(code=f"MI-DEMO-FAM-{suffix}", name="Demo family (fictitious)")
    db.add(family)
    db.flush()
    part = PartNumber(product_family_id=family.id, code=f"MI-DEMO-{suffix}", name="Demo bracket")
    db.add(part)
    classification = CharacteristicClassification(code=f"CLS-{suffix}", name="Demo classification")
    db.add(classification)
    db.flush()
    characteristic = Characteristic(
        part_number_id=part.id,
        balloon_number="1",
        name="Demo diameter",
        characteristic_type="diameter",
        unit="mm",
        classification_id=classification.id,
    )
    db.add(characteristic)
    db.flush()
    db.add(
        Specification(characteristic_id=characteristic.id, nominal=10, lower_tol=-1, upper_tol=1, unit="mm")
    )
    plan = InspectionPlan(part_number_id=part.id, name="Demo plan")
    db.add(plan)
    db.flush()
    return {"part": part, "characteristic": characteristic, "plan": plan}


@pytest.fixture
def demo_frequency_recommendation() -> dict:
    """A pending frequency_decrease recommendation with a pre-existing
    active InspectionFrequency (so the accept flow's "close old, open new"
    behavior is actually exercised, not just an insert into empty state)."""
    db = SessionLocal()
    try:
        ctx = _make_catalog(db)
        old_frequency = InspectionFrequency(
            inspection_plan_id=ctx["plan"].id,
            characteristic_id=ctx["characteristic"].id,
            frequency_type="every_n_parts",
            frequency_value=5,
        )
        db.add(old_frequency)
        db.flush()
        risk = RiskAssessment(
            characteristic_id=ctx["characteristic"].id,
            score=15,
            level="low",
            factors={"cpk": 1.8},
            engine_name="risk-demo",
            engine_version="0.1.0",
        )
        db.add(risk)
        db.flush()
        recommendation = Recommendation(
            characteristic_id=ctx["characteristic"].id,
            risk_assessment_id=risk.id,
            recommendation_type="frequency_decrease",
            rationale="Cpk consistently above 1.67 for 90 days.",
            evidence={"proposed_frequency_type": "every_n_parts", "proposed_frequency_value": 10},
            engine_name="adaptive-inspection-demo",
            engine_version="0.1.0",
        )
        db.add(recommendation)
        db.commit()
        return {
            **ctx,
            "old_frequency_id": old_frequency.id,
            "recommendation_id": recommendation.id,
            "characteristic_id": ctx["characteristic"].id,
        }
    finally:
        db.close()


@pytest.fixture
def demo_non_frequency_recommendation() -> uuid.UUID:
    db = SessionLocal()
    try:
        ctx = _make_catalog(db)
        recommendation = Recommendation(
            characteristic_id=ctx["characteristic"].id,
            recommendation_type="investigate_cause",
            rationale="Slow drift detected toward upper limit.",
            evidence={"triggering_result_ids": [str(uuid.uuid4())]},
            engine_name="risk-demo",
            engine_version="0.1.0",
        )
        db.add(recommendation)
        db.commit()
        return recommendation.id
    finally:
        db.close()


def _audit_actions(entity_type: str, entity_id: uuid.UUID) -> list[str]:
    db = SessionLocal()
    try:
        stmt = sa.select(AuditLog.action).where(
            AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id
        )
        return list(db.execute(stmt).scalars().all())
    finally:
        db.close()


# --- Accept -> frequency end to end -------------------------------------------


def test_accepting_frequency_recommendation_creates_linked_inspection_frequency(
    intelligence_client: TestClient, as_role, demo_frequency_recommendation: dict
) -> None:
    rec_id = demo_frequency_recommendation["recommendation_id"]
    response = intelligence_client.post(
        f"/api/v1/recommendations/{rec_id}/decision",
        headers=as_role("quality_engineer"),
        json={"action": "accepted", "comment": "Stable process, reducing sampling frequency."},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recommendation"]["state"] == "accepted"
    assert body["decision"]["action"] == "accepted"
    assert body["decision"]["comment"] == "Stable process, reducing sampling frequency."
    assert body["inspection_frequency_id"] is not None

    db = SessionLocal()
    try:
        new_freq = db.get(InspectionFrequency, uuid.UUID(body["inspection_frequency_id"]))
        assert new_freq.frequency_value == 10
        assert new_freq.valid_to is None
        assert str(new_freq.decision_id) == body["decision"]["id"]

        old_freq = db.get(InspectionFrequency, demo_frequency_recommendation["old_frequency_id"])
        assert old_freq.valid_to is not None, "the previously active frequency must be closed, not deleted"
        assert old_freq.frequency_value == 5, "history is preserved, not overwritten"
    finally:
        db.close()

    assert "create_version" in _audit_actions(
        "catalog.inspection_frequency", uuid.UUID(body["inspection_frequency_id"])
    )
    assert "decided" in _audit_actions("intelligence.recommendation", rec_id)


def test_rejecting_recommendation_does_not_touch_inspection_frequency(
    intelligence_client: TestClient, as_role, demo_frequency_recommendation: dict
) -> None:
    rec_id = demo_frequency_recommendation["recommendation_id"]
    response = intelligence_client.post(
        f"/api/v1/recommendations/{rec_id}/decision",
        headers=as_role("quality_engineer"),
        json={"action": "rejected", "comment": "Not enough history yet to justify a change."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["recommendation"]["state"] == "rejected"
    assert body["inspection_frequency_id"] is None

    db = SessionLocal()
    try:
        old_freq = db.get(InspectionFrequency, demo_frequency_recommendation["old_frequency_id"])
        assert old_freq.valid_to is None, "rejecting must never touch operational state (CLAUDE.md §2/§24)"
    finally:
        db.close()


def test_accepting_non_frequency_recommendation_does_not_create_frequency(
    intelligence_client: TestClient, as_role, demo_non_frequency_recommendation: uuid.UUID
) -> None:
    response = intelligence_client.post(
        f"/api/v1/recommendations/{demo_non_frequency_recommendation}/decision",
        headers=as_role("admin"),
        json={"action": "accepted", "comment": "Investigating with the process engineer."},
    )
    assert response.status_code == 200
    assert response.json()["inspection_frequency_id"] is None


# --- State machine -------------------------------------------------------------


def test_deciding_an_already_decided_recommendation_is_rejected(
    intelligence_client: TestClient, as_role, demo_non_frequency_recommendation: uuid.UUID
) -> None:
    headers = as_role("admin")
    first = intelligence_client.post(
        f"/api/v1/recommendations/{demo_non_frequency_recommendation}/decision",
        headers=headers,
        json={"action": "accepted", "comment": "First decision."},
    )
    assert first.status_code == 200

    second = intelligence_client.post(
        f"/api/v1/recommendations/{demo_non_frequency_recommendation}/decision",
        headers=headers,
        json={"action": "rejected", "comment": "Trying to decide again."},
    )
    assert second.status_code == 409
    assert "pending" in second.json()["detail"].lower()


def test_comment_is_required(
    intelligence_client: TestClient, as_role, demo_non_frequency_recommendation: uuid.UUID
) -> None:
    response = intelligence_client.post(
        f"/api/v1/recommendations/{demo_non_frequency_recommendation}/decision",
        headers=as_role("admin"),
        json={"action": "accepted", "comment": ""},
    )
    assert response.status_code == 422


def test_decision_row_is_immutable_at_the_db_level(
    intelligence_client: TestClient, as_role, demo_non_frequency_recommendation: uuid.UUID
) -> None:
    """Defense in depth: even if application code had a bug, the DB trigger
    (migration 0004) must still block direct mutation of a Decision."""
    response = intelligence_client.post(
        f"/api/v1/recommendations/{demo_non_frequency_recommendation}/decision",
        headers=as_role("admin"),
        json={"action": "accepted", "comment": "For the immutability check."},
    )
    decision_id = uuid.UUID(response.json()["decision"]["id"])

    db = SessionLocal()
    try:
        with pytest.raises(sa.exc.DBAPIError, match="append-only"):
            db.execute(
                sa.text("UPDATE intelligence_decisions SET comment = 'tampered' WHERE id = :id"),
                {"id": decision_id},
            )
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_superseding_marks_other_pending_recommendations_of_same_type_and_characteristic(
    intelligence_client: TestClient, as_role
) -> None:
    db = SessionLocal()
    try:
        ctx = _make_catalog(db)
        rec_a = Recommendation(
            characteristic_id=ctx["characteristic"].id,
            recommendation_type="frequency_increase",
            rationale="High variance detected.",
            evidence={"proposed_frequency_type": "every_n_parts", "proposed_frequency_value": 2},
            engine_name="risk-demo",
            engine_version="0.1.0",
        )
        rec_b = Recommendation(
            characteristic_id=ctx["characteristic"].id,
            recommendation_type="frequency_increase",
            rationale="High variance detected (re-evaluated).",
            evidence={"proposed_frequency_type": "every_n_parts", "proposed_frequency_value": 3},
            engine_name="risk-demo",
            engine_version="0.1.1",
        )
        unrelated = Recommendation(
            characteristic_id=ctx["characteristic"].id,
            recommendation_type="investigate_cause",
            rationale="Different recommendation type -- must not be superseded.",
            evidence={},
            engine_name="risk-demo",
            engine_version="0.1.0",
        )
        db.add_all([rec_a, rec_b, unrelated])
        db.commit()
        rec_a_id, rec_b_id, unrelated_id = rec_a.id, rec_b.id, unrelated.id
        characteristic_id = ctx["characteristic"].id
    finally:
        db.close()

    response = intelligence_client.post(
        f"/api/v1/recommendations/{rec_a_id}/decision",
        headers=as_role("quality_engineer"),
        json={"action": "accepted", "comment": "Accepting the earlier, still-valid recommendation."},
    )
    assert response.status_code == 200
    assert response.json()["superseded_recommendation_ids"] == [str(rec_b_id)]

    pending_list = intelligence_client.get(
        "/api/v1/recommendations",
        params={"characteristic_id": str(characteristic_id), "state": "pending"},
        headers=as_role("auditor"),
    ).json()
    pending_ids = {item["id"] for item in pending_list["items"]}
    assert str(rec_b_id) not in pending_ids, "superseded recommendation must drop out of the pending inbox"
    assert str(unrelated_id) in pending_ids, "a different recommendation_type must stay pending"

    db = SessionLocal()
    try:
        assert db.get(Recommendation, rec_b_id).state == "superseded"
        assert db.get(Recommendation, unrelated_id).state == "pending", (
            "different type must not be superseded"
        )
    finally:
        db.close()


def test_deciding_a_superseded_recommendation_is_rejected(intelligence_client: TestClient, as_role) -> None:
    db = SessionLocal()
    try:
        ctx = _make_catalog(db)
        rec_a = Recommendation(
            characteristic_id=ctx["characteristic"].id,
            recommendation_type="immediate_inspection",
            rationale="NOK outlier detected.",
            evidence={},
            engine_name="risk-demo",
            engine_version="0.1.0",
        )
        rec_b = Recommendation(
            characteristic_id=ctx["characteristic"].id,
            recommendation_type="immediate_inspection",
            rationale="NOK outlier detected (re-evaluated).",
            evidence={},
            engine_name="risk-demo",
            engine_version="0.1.0",
        )
        db.add_all([rec_a, rec_b])
        db.commit()
        rec_a_id, rec_b_id = rec_a.id, rec_b.id
    finally:
        db.close()

    headers = as_role("quality_engineer")
    accept = intelligence_client.post(
        f"/api/v1/recommendations/{rec_a_id}/decision",
        headers=headers,
        json={"action": "accepted", "comment": "Inspecting now."},
    )
    assert accept.status_code == 200
    assert accept.json()["superseded_recommendation_ids"] == [str(rec_b_id)]

    decide_superseded = intelligence_client.post(
        f"/api/v1/recommendations/{rec_b_id}/decision",
        headers=headers,
        json={"action": "accepted", "comment": "Trying to decide on a superseded one."},
    )
    assert decide_superseded.status_code == 409


# --- Missing-evidence / no-plan error paths -----------------------------------


def test_frequency_recommendation_missing_evidence_returns_clear_422(
    intelligence_client: TestClient, as_role
) -> None:
    db = SessionLocal()
    try:
        ctx = _make_catalog(db)
        recommendation = Recommendation(
            characteristic_id=ctx["characteristic"].id,
            recommendation_type="frequency_decrease",
            rationale="Missing evidence on purpose for this test.",
            evidence={},
            engine_name="risk-demo",
            engine_version="0.1.0",
        )
        db.add(recommendation)
        db.commit()
        rec_id = recommendation.id
    finally:
        db.close()

    response = intelligence_client.post(
        f"/api/v1/recommendations/{rec_id}/decision",
        headers=as_role("admin"),
        json={"action": "accepted", "comment": "Accepting despite missing evidence."},
    )
    assert response.status_code == 422
    assert "evidence" in response.json()["detail"].lower()


# --- Decision Memory: action taken ---------------------------------------------


def test_action_taken_appends_rows_and_never_updates(
    intelligence_client: TestClient, as_role, demo_non_frequency_recommendation: uuid.UUID
) -> None:
    decide_response = intelligence_client.post(
        f"/api/v1/recommendations/{demo_non_frequency_recommendation}/decision",
        headers=as_role("admin"),
        json={"action": "accepted", "comment": "Will follow up with an action."},
    )
    decision_id = decide_response.json()["decision"]["id"]

    first = intelligence_client.post(
        f"/api/v1/decisions/{decision_id}/actions",
        headers=as_role("quality_engineer"),
        json={"description": "Scheduled a follow-up inspection."},
    )
    assert first.status_code == 201
    assert first.json()["outcome_status"] == "pending"

    second = intelligence_client.post(
        f"/api/v1/decisions/{decision_id}/actions",
        headers=as_role("quality_engineer"),
        json={"description": "Follow-up complete: cause found and corrected.", "outcome_status": "effective"},
    )
    assert second.status_code == 201
    assert second.json()["id"] != first.json()["id"]

    detail = intelligence_client.get(
        f"/api/v1/recommendations/{demo_non_frequency_recommendation}", headers=as_role("quality_engineer")
    )
    assert len(detail.json()["decision"]["actions_taken"]) == 2


def test_action_taken_requires_an_existing_decision(intelligence_client: TestClient, as_role) -> None:
    response = intelligence_client.post(
        f"/api/v1/decisions/{uuid.uuid4()}/actions",
        headers=as_role("admin"),
        json={"description": "Orphan action."},
    )
    assert response.status_code == 404


# --- RBAC ------------------------------------------------------------------


def test_unauthenticated_requests_rejected(intelligence_client: TestClient) -> None:
    assert intelligence_client.get("/api/v1/recommendations").status_code == 401


def test_viewer_cannot_read_recommendations(intelligence_client: TestClient, as_role) -> None:
    response = intelligence_client.get("/api/v1/recommendations", headers=as_role("viewer"))
    assert response.status_code == 403


@pytest.mark.parametrize("role", ["viewer", "metrologist"])
def test_viewer_and_metrologist_cannot_decide(
    intelligence_client: TestClient, as_role, demo_non_frequency_recommendation: uuid.UUID, role: str
) -> None:
    response = intelligence_client.post(
        f"/api/v1/recommendations/{demo_non_frequency_recommendation}/decision",
        headers=as_role(role),
        json={"action": "accepted", "comment": "Should be denied."},
    )
    assert response.status_code == 403


@pytest.mark.parametrize("role", ["quality_engineer", "admin"])
def test_qe_and_admin_can_decide(
    intelligence_client: TestClient, as_role, demo_non_frequency_recommendation: uuid.UUID, role: str
) -> None:
    response = intelligence_client.post(
        f"/api/v1/recommendations/{demo_non_frequency_recommendation}/decision",
        headers=as_role(role),
        json={"action": "accepted", "comment": f"Accepted by {role}."},
    )
    assert response.status_code == 200


def test_metrologist_cannot_record_action_taken(
    intelligence_client: TestClient, as_role, demo_non_frequency_recommendation: uuid.UUID
) -> None:
    decide_response = intelligence_client.post(
        f"/api/v1/recommendations/{demo_non_frequency_recommendation}/decision",
        headers=as_role("admin"),
        json={"action": "accepted", "comment": "Setting up for the RBAC check."},
    )
    decision_id = decide_response.json()["decision"]["id"]

    response = intelligence_client.post(
        f"/api/v1/decisions/{decision_id}/actions",
        headers=as_role("metrologist"),
        json={"description": "Should be denied."},
    )
    assert response.status_code == 403
