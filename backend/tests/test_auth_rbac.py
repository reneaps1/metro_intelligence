"""F4.2 (MI-22): RBAC matrix + /me contract tests.

The parametrized matrix is derived from the migration's ``ROLE_PERMISSIONS``
dict (the source of truth for the RBAC contract, importable without a DB) and
exercised through the real ``require_permission`` dependency. Because the DB is
seeded from that same dict, the test cross-checks source vs. what was actually
loaded.

Contract items from docs/security/rbac.md ("Test Contract For F4.2") covered
here:
- Every role x permission token returns 200 (allowed) or 403 (denied).
- Unauthenticated access to a protected endpoint returns 401.
- No role can update/delete MeasurementRun/Sample/Result (no such token exists).
- viewer / metrologist / auditor cannot call decision endpoints.
- auditor has no successful write/update/decide/administer endpoint.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest
import sqlalchemy as sa
from app.core.database import SessionLocal

from conftest import DEMO_USERS

ROLES = ["viewer", "metrologist", "quality_engineer", "admin", "auditor"]


def _load_role_permissions() -> dict:
    path = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0001_org_security.py"
    spec = importlib.util.spec_from_file_location("migration_0001_org_security", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module.ROLE_PERMISSIONS


ROLE_PERMISSIONS = _load_role_permissions()


def _matrix_cases():
    cases = []
    for resource, actions in ROLE_PERMISSIONS.items():
        for action, roles in actions.items():
            token = f"{resource}.{action}"
            for role in ROLES:
                cases.append((role, token, role in roles))
    return cases


@pytest.fixture(scope="session")
def db_tokens(auth_database):
    db = SessionLocal()
    try:
        tokens = [r[0] for r in db.execute(sa.text("SELECT token FROM security_permissions")).all()]
    finally:
        db.close()
    return set(tokens)


@pytest.mark.parametrize("role,token,expected", _matrix_cases())
def test_rbac_matrix(role, token, expected, role_tokens, client):
    access = role_tokens(role)
    resource, _, action = token.rpartition(".")
    response = client.get(
        f"/perm/{resource}/{action}",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert response.status_code == (200 if expected else 403), (
        f"{role} -> {token}: expected {'200' if expected else '403'} " f"got {response.status_code}"
    )


def test_unauthenticated_protected_endpoint_returns_401(client):
    token = next(iter(ROLE_PERMISSIONS)) + ".read"
    resource, _, action = token.rpartition(".")
    response = client.get(f"/perm/{resource}/{action}")
    assert response.status_code == 401


def test_me_requires_auth_and_returns_roles(client, role_tokens):
    assert client.get("/auth/me").status_code == 401

    headers = {"Authorization": f"Bearer {role_tokens('admin')}"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == DEMO_USERS["admin"]
    assert "admin" in body["roles"]
    assert body["is_active"] is True


def test_no_update_or_delete_tokens_for_immutable_measurements(db_tokens):
    for resource in (
        "measurement.measurement_run",
        "measurement.measurement_sample",
        "measurement.measurement_result",
    ):
        assert f"{resource}.update" not in db_tokens
        assert f"{resource}.delete" not in db_tokens


def test_non_qe_cannot_decide_recommendations(client, role_tokens):
    for role in ("viewer", "metrologist", "auditor"):
        headers = {"Authorization": f"Bearer {role_tokens(role)}"}
        response = client.get("/perm/intelligence.recommendation/decide", headers=headers)
        assert response.status_code == 403, f"{role} should not decide"


def test_auditor_has_no_write_endpoints(client, role_tokens, db_tokens):
    write_actions = {"create", "update", "decide", "administer"}
    headers = {"Authorization": f"Bearer {role_tokens('auditor')}"}
    tokens = [t for t in db_tokens if t.rpartition(".")[2] in write_actions]
    assert tokens, "expected some write tokens to exist"
    for token in tokens:
        resource, _, action = token.rpartition(".")
        response = client.get(f"/perm/{resource}/{action}", headers=headers)
        assert response.status_code == 403, f"auditor allowed write {token}"
