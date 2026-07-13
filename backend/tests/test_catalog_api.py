"""F4.4 (MI-24): catalog CRUD API integration tests against a real PostgreSQL.

Reuses the disposable auth DB + demo users/migrations set up by conftest.py's
session-scoped ``auth_database`` fixture (autouse) and its ``DEMO_USERS`` /
``KNOWN_PASSWORD`` constants. Builds a dedicated test app mounting the real
``auth``/``catalog``/``users`` routers (mirroring conftest.py's ``auth_app``
pattern for F4.2) so requests exercise the actual RBAC dependency, versioning
logic, and DB constraints end to end -- not a mocked substitute.

Acceptance criteria covered (docs/tasks/F4.4.md):
- Editing a tolerance creates a new spec version; history stays intact.
- The RBAC matrix is verified by test on these endpoints.
- Validations (lower < nominal < upper, unique balloon) return clear 422s.
- Writes are audited with before/after.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from app.api.v1.auth import router as auth_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.users import router as users_router
from app.core.database import SessionLocal
from app.core.ratelimit import limiter
from app.models.security import AuditLog
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from conftest import DEMO_USERS, KNOWN_PASSWORD


@pytest.fixture(scope="session")
def catalog_app(auth_database: None) -> FastAPI:
    app = FastAPI(title="F4.4 catalog test app")
    app.include_router(auth_router)
    app.include_router(catalog_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    return app


@pytest.fixture(scope="session")
def catalog_client(catalog_app: FastAPI) -> TestClient:
    return TestClient(catalog_app)


@pytest.fixture(scope="session")
def as_role(catalog_client: TestClient):
    """Return a helper that logs in as ``role`` and yields auth headers.

    One login per role, cached for the whole session -- like conftest.py's
    ``role_tokens`` fixture for the same reason: this suite calls it far more
    than 30 times (the ``/auth/login`` rate limit per minute), so a fresh
    login per call would trip 429s well before the matrix/versioning tests
    finish."""
    cache: dict[str, dict[str, str]] = {}

    def _login(role: str) -> dict[str, str]:
        if role not in cache:
            response = catalog_client.post(
                "/auth/login",
                data={"username": DEMO_USERS[role], "password": KNOWN_PASSWORD},
            )
            assert response.status_code == 200, response.text
            token = response.json()["access_token"]
            cache[role] = {"Authorization": f"Bearer {token}"}
        return cache[role]

    return _login


def _unique_code(prefix: str) -> str:
    return f"MI-DEMO-{prefix}-{uuid.uuid4().hex[:8].upper()}"


def _create_family(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.post(
        "/api/v1/catalog/product-families",
        headers=headers,
        json={"code": _unique_code("FAM"), "name": "Demo family (fictitious)"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_part(client: TestClient, headers: dict[str, str], family_id: str) -> dict:
    response = client.post(
        "/api/v1/catalog/part-numbers",
        headers=headers,
        json={
            "product_family_id": family_id,
            "code": _unique_code("PN"),
            "name": "Demo bracket (fictitious)",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_classification(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.post(
        "/api/v1/catalog/characteristic-classifications",
        headers=headers,
        json={"code": _unique_code("CLS"), "name": "Demo classification"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_characteristic(
    client: TestClient,
    headers: dict[str, str],
    part_id: str,
    classification_id: str,
    balloon_number: str = "1",
) -> dict:
    response = client.post(
        "/api/v1/catalog/characteristics",
        headers=headers,
        json={
            "part_number_id": part_id,
            "balloon_number": balloon_number,
            "name": "Demo diameter",
            "characteristic_type": "diameter",
            "unit": "mm",
            "classification_id": classification_id,
            "specification": {"nominal": "10.000", "lower_tol": "-0.050", "upper_tol": "0.050", "unit": "mm"},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def catalog_fixture(catalog_client: TestClient, as_role):
    """One family/part/classification/characteristic, ready for spec tests."""
    admin_headers = as_role("admin")
    family = _create_family(catalog_client, admin_headers)
    part = _create_part(catalog_client, admin_headers, family["id"])
    classification = _create_classification(catalog_client, admin_headers)
    characteristic = _create_characteristic(catalog_client, admin_headers, part["id"], classification["id"])
    return {
        "admin_headers": admin_headers,
        "family": family,
        "part": part,
        "classification": classification,
        "characteristic": characteristic,
    }


# --- Basic CRUD + uniqueness --------------------------------------------------


def test_create_product_family_as_admin(catalog_client: TestClient, as_role) -> None:
    family = _create_family(catalog_client, as_role("admin"))
    assert family["code"].startswith("MI-DEMO-FAM-")

    response = catalog_client.get(
        f"/api/v1/catalog/product-families/{family['id']}", headers=as_role("viewer")
    )
    assert response.status_code == 200
    assert response.json()["id"] == family["id"]


def test_duplicate_product_family_code_returns_clear_422(catalog_client: TestClient, as_role) -> None:
    admin_headers = as_role("admin")
    code = _unique_code("FAM")
    payload = {"code": code, "name": "Demo family (fictitious)"}
    first = catalog_client.post("/api/v1/catalog/product-families", headers=admin_headers, json=payload)
    assert first.status_code == 201

    second = catalog_client.post("/api/v1/catalog/product-families", headers=admin_headers, json=payload)
    assert second.status_code == 422
    assert "already exists" in second.json()["detail"]


def test_duplicate_balloon_number_returns_clear_422(
    catalog_client: TestClient, catalog_fixture: dict
) -> None:
    admin_headers = catalog_fixture["admin_headers"]
    part_id = catalog_fixture["part"]["id"]
    classification_id = catalog_fixture["classification"]["id"]
    balloon = catalog_fixture["characteristic"]["balloon_number"]

    response = catalog_client.post(
        "/api/v1/catalog/characteristics",
        headers=admin_headers,
        json={
            "part_number_id": part_id,
            "balloon_number": balloon,
            "name": "Duplicate balloon",
            "characteristic_type": "diameter",
            "unit": "mm",
            "classification_id": classification_id,
            "specification": {"nominal": "5.0", "lower_tol": "-0.1", "upper_tol": "0.1", "unit": "mm"},
        },
    )
    assert response.status_code == 422
    assert "balloon" in response.json()["detail"].lower()


@pytest.mark.parametrize(
    "spec",
    [
        {"nominal": "10.0", "lower_tol": None, "upper_tol": None, "unit": "mm"},
        {"nominal": "10.0", "lower_tol": "0.05", "upper_tol": None, "unit": "mm"},  # lower_tol above nominal
        {"nominal": "10.0", "lower_tol": None, "upper_tol": "-0.05", "unit": "mm"},  # upper_tol below nominal
        {"nominal": "10.0", "lower_tol": "0.1", "upper_tol": "-0.1", "unit": "mm"},  # crossed limits
    ],
)
def test_specification_tolerance_validation_rejects_invalid_bounds(
    catalog_client: TestClient, catalog_fixture: dict, spec: dict
) -> None:
    characteristic_id = catalog_fixture["characteristic"]["id"]
    response = catalog_client.post(
        f"/api/v1/catalog/characteristics/{characteristic_id}/specifications",
        headers=catalog_fixture["admin_headers"],
        json=spec,
    )
    assert response.status_code == 422


# --- Versioning: editing a tolerance creates a new version, history intact --


def test_new_specification_version_closes_previous_and_keeps_history(
    catalog_client: TestClient, catalog_fixture: dict
) -> None:
    characteristic_id = catalog_fixture["characteristic"]["id"]
    admin_headers = catalog_fixture["admin_headers"]
    original_spec_id = catalog_fixture["characteristic"]["active_specification"]["id"]

    response = catalog_client.post(
        f"/api/v1/catalog/characteristics/{characteristic_id}/specifications",
        headers=admin_headers,
        json={"nominal": "10.000", "lower_tol": "-0.030", "upper_tol": "0.030", "unit": "mm"},
    )
    assert response.status_code == 201
    new_spec = response.json()
    assert new_spec["id"] != original_spec_id
    assert new_spec["valid_to"] is None

    history = catalog_client.get(
        f"/api/v1/catalog/characteristics/{characteristic_id}/specifications",
        headers=admin_headers,
    ).json()
    by_id = {row["id"]: row for row in history}

    assert len(history) == 2, "original + new version must both still exist"
    assert by_id[original_spec_id]["valid_to"] is not None, "original version must be closed, not deleted"
    assert by_id[original_spec_id]["nominal"] == "10.000000", "closed version's own data is untouched"
    assert by_id[new_spec["id"]]["valid_to"] is None

    active = catalog_client.get(
        f"/api/v1/catalog/characteristics/{characteristic_id}",
        headers=admin_headers,
    ).json()["active_specification"]
    assert active["id"] == new_spec["id"]


def test_new_measurement_program_version_increments_and_closes_previous(
    catalog_client: TestClient, catalog_fixture: dict
) -> None:
    admin_headers = catalog_fixture["admin_headers"]
    part_id = catalog_fixture["part"]["id"]

    first = catalog_client.post(
        f"/api/v1/catalog/part-numbers/{part_id}/measurement-programs",
        headers=admin_headers,
        json={"name": "PW-Routine-Demo", "output_mapping": {"col_1": "balloon_1"}},
    )
    assert first.status_code == 201
    assert first.json()["version"] == 1

    second = catalog_client.post(
        f"/api/v1/catalog/part-numbers/{part_id}/measurement-programs",
        headers=admin_headers,
        json={"name": "PW-Routine-Demo", "output_mapping": {"col_1": "balloon_1", "col_2": "balloon_2"}},
    )
    assert second.status_code == 201
    assert second.json()["version"] == 2
    assert second.json()["valid_to"] is None

    programs = catalog_client.get(
        f"/api/v1/catalog/part-numbers/{part_id}/measurement-programs",
        headers=admin_headers,
    ).json()
    assert len(programs) == 2
    closed = next(p for p in programs if p["version"] == 1)
    assert closed["valid_to"] is not None


def test_new_inspection_frequency_version_records_actor_and_closes_previous(
    catalog_client: TestClient, catalog_fixture: dict, as_role
) -> None:
    qe_headers = as_role("quality_engineer")
    part_id = catalog_fixture["part"]["id"]
    characteristic_id = catalog_fixture["characteristic"]["id"]

    plan_response = catalog_client.post(
        "/api/v1/catalog/inspection-plans",
        headers=qe_headers,
        json={"part_number_id": part_id, "name": "Demo plan"},
    )
    assert plan_response.status_code == 201
    plan_id = plan_response.json()["id"]

    first = catalog_client.post(
        f"/api/v1/catalog/inspection-plans/{plan_id}/frequencies",
        headers=qe_headers,
        json={
            "characteristic_id": characteristic_id,
            "frequency_type": "every_n_parts",
            "frequency_value": "5",
        },
    )
    assert first.status_code == 201
    assert first.json()["changed_by_user_id"] is not None

    second = catalog_client.post(
        f"/api/v1/catalog/inspection-plans/{plan_id}/frequencies",
        headers=qe_headers,
        json={
            "characteristic_id": characteristic_id,
            "frequency_type": "every_n_parts",
            "frequency_value": "10",
            "reason": "Stable Cpk over last 90 days (demo).",
        },
    )
    assert second.status_code == 201

    history = catalog_client.get(
        f"/api/v1/catalog/inspection-plans/{plan_id}/frequencies",
        headers=qe_headers,
    ).json()
    assert len(history) == 2
    closed = next(row for row in history if row["id"] == first.json()["id"])
    assert closed["valid_to"] is not None


def test_inspection_frequency_rejects_non_positive_value(
    catalog_client: TestClient, catalog_fixture: dict, as_role
) -> None:
    qe_headers = as_role("quality_engineer")
    plan_response = catalog_client.post(
        "/api/v1/catalog/inspection-plans",
        headers=qe_headers,
        json={"part_number_id": catalog_fixture["part"]["id"], "name": "Demo plan zero"},
    )
    assert plan_response.status_code == 201

    response = catalog_client.post(
        f"/api/v1/catalog/inspection-plans/{plan_response.json()['id']}/frequencies",
        headers=qe_headers,
        json={
            "characteristic_id": catalog_fixture["characteristic"]["id"],
            "frequency_type": "every_n_parts",
            "frequency_value": "0",
        },
    )
    assert response.status_code == 422


# --- RBAC ----------------------------------------------------------------------


def test_unauthenticated_request_returns_401(catalog_client: TestClient) -> None:
    response = catalog_client.get("/api/v1/catalog/product-families")
    assert response.status_code == 401


@pytest.mark.parametrize(
    "role,expected",
    [("viewer", 200), ("metrologist", 200), ("quality_engineer", 200), ("admin", 200), ("auditor", 200)],
)
def test_every_role_can_read_product_families(
    catalog_client: TestClient, as_role, role: str, expected: int
) -> None:
    response = catalog_client.get("/api/v1/catalog/product-families", headers=as_role(role))
    assert response.status_code == expected


@pytest.mark.parametrize("role", ["viewer", "metrologist", "quality_engineer", "auditor"])
def test_only_admin_can_create_product_family(catalog_client: TestClient, as_role, role: str) -> None:
    response = catalog_client.post(
        "/api/v1/catalog/product-families",
        headers=as_role(role),
        json={"code": _unique_code("FAM"), "name": "Should be denied"},
    )
    assert response.status_code == 403


@pytest.mark.parametrize("role", ["quality_engineer", "admin"])
def test_qe_and_admin_can_create_inspection_plans(
    catalog_client: TestClient, catalog_fixture: dict, as_role, role: str
) -> None:
    response = catalog_client.post(
        "/api/v1/catalog/inspection-plans",
        headers=as_role(role),
        json={"part_number_id": catalog_fixture["part"]["id"], "name": f"Demo plan {role}"},
    )
    assert response.status_code == 201


@pytest.mark.parametrize("role", ["viewer", "metrologist", "auditor"])
def test_viewer_metrologist_auditor_cannot_create_inspection_plans(
    catalog_client: TestClient, catalog_fixture: dict, as_role, role: str
) -> None:
    response = catalog_client.post(
        "/api/v1/catalog/inspection-plans",
        headers=as_role(role),
        json={"part_number_id": catalog_fixture["part"]["id"], "name": f"Demo plan {role}"},
    )
    assert response.status_code == 403


def test_auditor_can_read_users_but_not_create(catalog_client: TestClient, as_role) -> None:
    auditor_headers = as_role("auditor")
    assert catalog_client.get("/api/v1/users", headers=auditor_headers).status_code == 200

    response = catalog_client.post(
        "/api/v1/users",
        headers=auditor_headers,
        json={
            "email": "new.demo.user@demo.local",
            "display_name": "Demo User",
            "password": "SomeStrongPassw0rd!",
            "role_names": ["viewer"],
        },
    )
    assert response.status_code == 403


# --- User admin ------------------------------------------------------------


def test_admin_creates_user_with_roles(catalog_client: TestClient, as_role) -> None:
    admin_headers = as_role("admin")
    email = f"demo.user.{uuid.uuid4().hex[:8]}@demo.local"
    response = catalog_client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": email,
            "display_name": "Demo Fictitious User",
            "password": "SomeStrongPassw0rd!",
            "role_names": ["viewer", "metrologist"],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == email
    assert set(body["roles"]) == {"viewer", "metrologist"}
    assert "password" not in body
    assert "password_hash" not in body


def test_create_user_with_unknown_role_returns_422(catalog_client: TestClient, as_role) -> None:
    response = catalog_client.post(
        "/api/v1/users",
        headers=as_role("admin"),
        json={
            "email": f"demo.user.{uuid.uuid4().hex[:8]}@demo.local",
            "display_name": "Demo User",
            "password": "SomeStrongPassw0rd!",
            "role_names": ["not_a_real_role"],
        },
    )
    assert response.status_code == 422


def test_duplicate_user_email_returns_clear_422(catalog_client: TestClient, as_role) -> None:
    admin_headers = as_role("admin")
    payload = {
        "email": f"demo.dup.{uuid.uuid4().hex[:8]}@demo.local",
        "display_name": "Demo User",
        "password": "SomeStrongPassw0rd!",
        "role_names": ["viewer"],
    }
    first = catalog_client.post("/api/v1/users", headers=admin_headers, json=payload)
    assert first.status_code == 201

    second = catalog_client.post("/api/v1/users", headers=admin_headers, json=payload)
    assert second.status_code == 422
    assert "already exists" in second.json()["detail"]


# --- Audit trail -------------------------------------------------------------


def _audit_entries_for(entity_type: str, entity_id: str) -> list[AuditLog]:
    db = SessionLocal()
    try:
        stmt = sa.select(AuditLog).where(
            AuditLog.entity_type == entity_type, AuditLog.entity_id == uuid.UUID(entity_id)
        )
        entries = list(db.execute(stmt).scalars().all())
        db.expunge_all()  # keep the rows usable after the session closes below
        return entries
    finally:
        db.close()


def test_product_family_update_is_audited_with_before_after(catalog_client: TestClient, as_role) -> None:
    admin_headers = as_role("admin")
    family = _create_family(catalog_client, admin_headers)

    response = catalog_client.patch(
        f"/api/v1/catalog/product-families/{family['id']}",
        headers=admin_headers,
        json={"name": "Renamed demo family"},
    )
    assert response.status_code == 200

    entries = _audit_entries_for("catalog.product_family", family["id"])
    update_entries = [e for e in entries if e.action == "update"]
    assert update_entries, "expected an audited update entry"
    entry = update_entries[-1]
    assert entry.before_state == {"name": family["name"]}
    assert entry.after_state == {"name": "Renamed demo family"}
    assert entry.actor_identifier == DEMO_USERS["admin"]


def test_specification_version_change_is_audited(catalog_client: TestClient, catalog_fixture: dict) -> None:
    characteristic_id = catalog_fixture["characteristic"]["id"]
    original_spec_id = catalog_fixture["characteristic"]["active_specification"]["id"]

    response = catalog_client.post(
        f"/api/v1/catalog/characteristics/{characteristic_id}/specifications",
        headers=catalog_fixture["admin_headers"],
        json={"nominal": "10.000", "lower_tol": "-0.020", "upper_tol": "0.020", "unit": "mm"},
    )
    assert response.status_code == 201
    new_spec_id = response.json()["id"]

    closed_entries = _audit_entries_for("catalog.specification", original_spec_id)
    assert any(e.action == "close_version" for e in closed_entries)

    created_entries = _audit_entries_for("catalog.specification", new_spec_id)
    assert any(e.action == "create_version" for e in created_entries)
