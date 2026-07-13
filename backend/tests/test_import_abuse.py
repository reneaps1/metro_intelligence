"""F4.5 (MI-25): file import abuse / security suite.

Acceptance criterion (docs/tasks/F4.5.md): "archivo gigante, ejecutable
renombrado, CSV con formulas, xlsx bomba -> todos rechazados con error
limpio y auditados." Each of those is a whole-file rejection (422), not a
per-row quarantine -- a crafted attack file is a different situation from
one bad data row in an otherwise-trustworthy export.

Reuses conftest.py's disposable, migrated Postgres + demo users (same
pattern as test_catalog_api.py: a dedicated FastAPI test app mounting the
real routers, ``get_object_storage`` overridden with an in-memory fake since
no live MinIO is available in this environment -- see this PR's description
for what that does and doesn't verify).
"""

from __future__ import annotations

import io
import uuid
import zipfile

import pytest
import sqlalchemy as sa
from app.api.v1.auth import router as auth_router
from app.api.v1.imports import router as imports_router
from app.core.database import SessionLocal
from app.core.ratelimit import limiter
from app.models.security import AuditLog
from app.services.import_service import MAX_FILE_SIZE_BYTES
from app.services.storage_service import get_object_storage
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from conftest import DEMO_USERS, KNOWN_PASSWORD


class FakeObjectStorage:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, bucket: str, object_key: str, data: bytes, content_type: str) -> None:
        self.objects[(bucket, object_key)] = data


@pytest.fixture(scope="session")
def fake_storage() -> FakeObjectStorage:
    return FakeObjectStorage()


@pytest.fixture(scope="session")
def imports_app(auth_database: None, fake_storage: FakeObjectStorage) -> FastAPI:
    app = FastAPI(title="F4.5 imports abuse test app")
    app.include_router(auth_router)
    app.include_router(imports_router, prefix="/api/v1")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.dependency_overrides[get_object_storage] = lambda: fake_storage
    return app


@pytest.fixture(scope="session")
def imports_client(imports_app: FastAPI) -> TestClient:
    return TestClient(imports_app)


@pytest.fixture(scope="session")
def as_role(imports_client: TestClient):
    cache: dict[str, dict[str, str]] = {}

    def _login(role: str) -> dict[str, str]:
        if role not in cache:
            response = imports_client.post(
                "/auth/login",
                data={"username": DEMO_USERS[role], "password": KNOWN_PASSWORD},
            )
            assert response.status_code == 200, response.text
            cache[role] = {"Authorization": f"Bearer {response.json()['access_token']}"}
        return cache[role]

    return _login


def _upload(client: TestClient, headers: dict[str, str], filename: str, content: bytes):
    return client.post(
        "/api/v1/imports",
        headers=headers,
        files={"file": (filename, content, "application/octet-stream")},
    )


def _last_audit_action(entity_type: str) -> str | None:
    db = SessionLocal()
    try:
        stmt = (
            sa.select(AuditLog.action)
            .where(AuditLog.entity_type == entity_type)
            .order_by(AuditLog.created_at.desc())
            .limit(1)
        )
        return db.execute(stmt).scalar_one_or_none()
    finally:
        db.close()


def _build_zip_bomb() -> bytes:
    """A minimal, structurally-valid-looking OOXML zip whose one real entry
    decompresses at >100:1 -- enough to trip the compression-ratio guard in
    XlsxConnector.validate() without needing to build a full workbook or
    actually inflate to the 200MB absolute cap in a test."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("bomb.bin", b"0" * 5_000_000)
    return buffer.getvalue()


# --- Whole-file rejections ----------------------------------------------------


def test_oversized_file_rejected(imports_client: TestClient, as_role) -> None:
    content = b"a" * (MAX_FILE_SIZE_BYTES + 1)
    response = _upload(imports_client, as_role("metrologist"), "huge.csv", content)
    assert response.status_code == 422
    assert "size" in response.json()["detail"].lower()
    assert _last_audit_action("measurement.imported_file") == "upload_rejected"


@pytest.mark.parametrize("filename", ["malware.csv", "malware.xlsx"])
def test_renamed_executable_rejected(imports_client: TestClient, as_role, filename: str) -> None:
    content = b"MZ" + b"\x00" * 128  # Windows PE header, not a real CSV/XLSX
    response = _upload(imports_client, as_role("metrologist"), filename, content)
    assert response.status_code == 422
    assert "valid" in response.json()["detail"].lower()
    assert _last_audit_action("measurement.imported_file") == "upload_rejected"


def test_csv_formula_injection_rejected(imports_client: TestClient, as_role) -> None:
    content = (
        b"part_number,batch_lot,run_at,machine_code,operator_identifier,sample_sequence,COL_1\n"
        b"MI-DEMO-9999,BATCH-1,2026-07-13T00:00:00+00:00,CMM-01,OP,1,=cmd|'/C calc'!A1\n"
    )
    response = _upload(imports_client, as_role("metrologist"), "attack.csv", content)
    assert response.status_code == 422
    assert "injection" in response.json()["detail"].lower()
    assert _last_audit_action("measurement.imported_file") == "upload_rejected"


def test_xlsx_zip_bomb_rejected(imports_client: TestClient, as_role) -> None:
    response = _upload(imports_client, as_role("metrologist"), "bomb.xlsx", _build_zip_bomb())
    assert response.status_code == 422
    assert "safety check" in response.json()["detail"].lower()
    assert _last_audit_action("measurement.imported_file") == "upload_rejected"


def test_unsupported_extension_rejected(imports_client: TestClient, as_role) -> None:
    response = _upload(imports_client, as_role("metrologist"), "data.txt", b"part_number\nMI-DEMO-1\n")
    assert response.status_code == 422
    assert "unsupported" in response.json()["detail"].lower()


def test_empty_file_rejected(imports_client: TestClient, as_role) -> None:
    response = _upload(imports_client, as_role("metrologist"), "empty.csv", b"")
    assert response.status_code == 422


def test_negative_measurement_values_are_not_flagged_as_injection(
    imports_client: TestClient, as_role
) -> None:
    """Regression guard: a legitimate negative deviation ('-0.03') must not
    trip the same defense as an actual formula-injection payload -- unlike
    the attack case above, this should clear validate() (it may still fail
    later for unrelated reasons, e.g. an unknown part_number, but never with
    an 'injection' error)."""
    content = (
        b"part_number,batch_lot,run_at,machine_code,operator_identifier,sample_sequence,COL_1\n"
        b"MI-DEMO-9999,BATCH-1,2026-07-13T00:00:00+00:00,CMM-01,OP,1,-0.029484\n"
    )
    response = _upload(imports_client, as_role("metrologist"), "negative_values.csv", content)
    assert response.status_code != 422 or "injection" not in response.json()["detail"].lower()


# --- Dedup ---------------------------------------------------------------------


def test_duplicate_upload_is_detected(imports_client: TestClient, as_role) -> None:
    content = (
        f"part_number,batch_lot,run_at,machine_code,operator_identifier,sample_sequence,COL_1\n"
        f"MI-DEMO-DEDUP-{uuid.uuid4().hex[:8]},B,2026-07-13T00:00:00+00:00,CMM-01,OP,1,1.0\n"
    ).encode()
    headers = as_role("metrologist")
    first = _upload(imports_client, headers, "dedup.csv", content)
    assert first.status_code == 201
    first_id = first.json()["id"]

    second = _upload(imports_client, headers, "dedup.csv", content)
    assert second.status_code == 409
    assert second.json()["detail"]["imported_file_id"] == first_id
    assert _last_audit_action("measurement.imported_file") == "upload_duplicate_detected"


# --- RBAC + auth -----------------------------------------------------------


def test_unauthenticated_upload_rejected(imports_client: TestClient) -> None:
    response = imports_client.post("/api/v1/imports", files={"file": ("x.csv", b"a", "text/csv")})
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["viewer", "quality_engineer", "auditor"])
def test_roles_without_create_permission_are_denied(imports_client: TestClient, as_role, role: str) -> None:
    response = _upload(imports_client, as_role(role), "denied.csv", b"part_number\nMI-DEMO-1\n")
    assert response.status_code == 403


def test_get_import_requires_read_permission(imports_client: TestClient) -> None:
    response = imports_client.get(f"/api/v1/imports/{uuid.uuid4()}")
    assert response.status_code == 401
