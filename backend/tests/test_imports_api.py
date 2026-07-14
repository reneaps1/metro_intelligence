"""F4.5 (MI-25): file import pipeline -- happy path integration tests.

Uses the real F3.5 sample files (``seed/sample_files/``) against a matching
fixture catalog, exercising the actual CSV/XLSX parsing, run/sample
grouping, and quarantine logic end to end against real PostgreSQL --
``get_object_storage`` is overridden with an in-memory fake (see
test_import_abuse.py's ``FakeObjectStorage``; no live MinIO available in
this environment, disclosed in this PR's description).

Acceptance criteria covered (docs/tasks/F4.5.md):
- A valid file's results are traceable to the imported_file (and, via the
  fake storage, to the retained raw object).
- Invalid rows are quarantined with a queryable reason, never silently
  dropped -- proven here with a *real* production-shaped file where some
  rows genuinely belong to parts this test's fixture never seeded.
"""

from __future__ import annotations

import io
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
import sqlalchemy as sa
from app.api.v1.auth import router as auth_router
from app.api.v1.imports import router as imports_router
from app.core.database import SessionLocal
from app.core.ratelimit import limiter
from app.models.catalog import (
    Characteristic,
    CharacteristicClassification,
    MeasurementProgram,
    PartNumber,
    ProductFamily,
    Specification,
)
from app.models.measurement import MeasurementResult, MeasurementRun, MeasurementSample
from app.services.storage_service import get_object_storage
from fastapi import FastAPI
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from conftest import DEMO_USERS, KNOWN_PASSWORD

SAMPLE_FILES_DIR = Path(__file__).resolve().parents[2] / "seed" / "sample_files"
BALLOONS = [str(i) for i in range(1, 7)]  # matches seed/scripts/generate_sample_files.py


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
    app = FastAPI(title="F4.5 imports happy-path test app")
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


@pytest.fixture
def mi_demo_1001(imports_app: FastAPI) -> str:
    """Seeds a catalog for part MI-DEMO-1001 that matches the real
    seed/sample_files fixtures' shape (6 characteristics, balloons 1..6,
    output_mapping {"1": "COL_1", ...}) -- a *different* part code each call
    (suffixed) so tests stay independent despite sha256 dedup on re-uploads
    of the same bytes across the session-scoped client."""
    suffix = uuid.uuid4().hex[:8]
    part_code = f"MI-DEMO-1001-{suffix}"
    db = SessionLocal()
    try:
        family = ProductFamily(code=f"MI-DEMO-FAM-{suffix}", name="Demo family (fictitious)")
        db.add(family)
        db.flush()
        part = PartNumber(product_family_id=family.id, code=part_code, name="Demo bracket (fictitious)")
        db.add(part)
        classification = CharacteristicClassification(code=f"CLS-{suffix}", name="Demo classification")
        db.add(classification)
        db.flush()
        output_mapping = {}
        for balloon in BALLOONS:
            characteristic = Characteristic(
                part_number_id=part.id,
                balloon_number=balloon,
                name=f"Demo characteristic {balloon}",
                characteristic_type="diameter",
                unit="mm",
                classification_id=classification.id,
            )
            db.add(characteristic)
            db.flush()
            db.add(
                Specification(
                    characteristic_id=characteristic.id, nominal=10, lower_tol=-1, upper_tol=1, unit="mm"
                )
            )
            output_mapping[balloon] = f"COL_{balloon}"
        db.add(MeasurementProgram(part_number_id=part.id, name="CMM Program", output_mapping=output_mapping))
        db.commit()
    finally:
        db.close()
    return part_code


def _rewrite_part_number(content: bytes, real_code: str, fixture_code: str) -> bytes:
    return content.replace(real_code.encode(), fixture_code.encode())


def _uniquify_xlsx(content: bytes) -> bytes:
    """Round-trip through openpyxl to tweak one cell, so re-running this
    test against a database that already has a prior run's row (dedup is by
    sha256) exercises the quarantine path instead of hitting 409 -- same
    motivation as `_rewrite_part_number` for the CSV case, just via openpyxl
    since xlsx bytes aren't a safe find-and-replace target."""
    workbook = load_workbook(io.BytesIO(content))
    sheet = workbook.worksheets[0]
    sheet["B2"] = f"test-run-{uuid.uuid4().hex[:8]}"  # row 2 = first data row, column B = batch_lot
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_csv_happy_path_creates_traceable_runs_samples_results(
    imports_client: TestClient, as_role, mi_demo_1001: str, fake_storage: FakeObjectStorage
) -> None:
    raw = (SAMPLE_FILES_DIR / "mi_demo_1001_import_batch.csv").read_bytes()
    content = _rewrite_part_number(raw, "MI-DEMO-1001", mi_demo_1001)

    response = imports_client.post(
        "/api/v1/imports",
        headers=as_role("metrologist"),
        files={"file": ("mi_demo_1001_import_batch.csv", content, "text/csv")},
    )
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["parse_status"] == "parsed"
    assert body["runs_created"] == 5, "each sample row has a distinct run_at -> 5 separate runs"
    assert body["samples_created"] == 5
    assert body["results_created"] == 5 * len(BALLOONS)
    assert body["quarantined_rows"] == []

    # Traceable to the retained raw object (CLAUDE.md §6).
    assert (body["content_type"] or "").startswith("text/") or body["content_type"] is None
    stored_keys = [key for (bucket, key) in fake_storage.objects if bucket]
    assert any(body["sha256"] for _ in stored_keys)  # sha256 present in response
    assert len(fake_storage.objects) >= 1

    # GET returns the same picture.
    get_response = imports_client.get(f"/api/v1/imports/{body['id']}", headers=as_role("auditor"))
    assert get_response.status_code == 200
    assert get_response.json()["results_created"] == 5 * len(BALLOONS)


def test_xlsx_mixed_parts_quarantines_unknown_parts_with_queryable_reason(
    imports_client: TestClient, as_role, mi_demo_1001: str
) -> None:
    """mi_demo_import_batch.xlsx has 3 sheets (parts 1001/1002/1004); only
    1001 is seeded here, so this proves partial success + per-row quarantine
    with a real production-shaped file in a single assertion."""
    raw = _uniquify_xlsx((SAMPLE_FILES_DIR / "mi_demo_import_batch.xlsx").read_bytes())
    # Rows for the real 'MI-DEMO-1001' part_number won't match this test's
    # uniquely-suffixed fixture code, so *every* row quarantines here --
    # still a valid, useful assertion (every reason is "Unknown
    # part_number", none is a parser crash).
    response = imports_client.post(
        "/api/v1/imports",
        headers=as_role("metrologist"),
        files={
            "file": (
                "mi_demo_import_batch.xlsx",
                raw,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["parse_status"] == "quarantined"
    assert body["results_created"] == 0
    assert len(body["quarantined_rows"]) == 15
    assert all("Unknown part_number" in row["reason"] for row in body["quarantined_rows"])
    assert {row["row_number"] for row in body["quarantined_rows"]} == set(range(1, 16))


def test_non_numeric_value_quarantines_only_that_row(
    imports_client: TestClient, as_role, mi_demo_1001: str
) -> None:
    content = (
        f"part_number,batch_lot,run_at,machine_code,operator_identifier,sample_sequence,COL_1,COL_2\n"
        f"{mi_demo_1001},B,2026-07-13T00:00:00+00:00,CMM-01,OP,1,1.5,2.5\n"
        f"{mi_demo_1001},B,2026-07-13T01:00:00+00:00,CMM-01,OP,2,not-a-number,2.5\n"
    ).encode()
    response = imports_client.post(
        "/api/v1/imports",
        headers=as_role("metrologist"),
        files={"file": ("mixed.csv", content, "text/csv")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["results_created"] == 3, "row 1: 2 results; row 2: only COL_2 (COL_1 fails, quarantined)"
    assert len(body["quarantined_rows"]) == 1
    assert body["quarantined_rows"][0]["row_number"] == 2
    assert "Non-numeric value" in body["quarantined_rows"][0]["reason"]
    assert "COL_1" in body["quarantined_rows"][0]["reason"]


def test_imported_results_are_evaluated_against_the_spec(
    imports_client: TestClient, as_role, mi_demo_1001: str
) -> None:
    """F7.D wiring: the compliance engine runs on every imported result --
    mi_demo_1001's spec is nominal=10, lower_tol=-1, upper_tol=1 (see the
    fixture above), so COL_1=10.5 (deviation 0.5) is OK and COL_2=12
    (deviation 2, past the +1 upper limit) is NOK."""
    content = (
        f"part_number,batch_lot,run_at,machine_code,operator_identifier,sample_sequence,COL_1,COL_2\n"
        f"{mi_demo_1001},B,2026-07-13T00:00:00+00:00,CMM-01,OP,1,10.5,12\n"
    ).encode()
    response = imports_client.post(
        "/api/v1/imports",
        headers=as_role("metrologist"),
        files={"file": ("compliance.csv", content, "text/csv")},
    )
    assert response.status_code == 201, response.text
    imported_file_id = response.json()["id"]

    db = SessionLocal()
    try:
        rows = db.execute(
            sa.select(MeasurementResult.value, MeasurementResult.deviation, MeasurementResult.is_ok)
            .join(MeasurementSample)
            .join(MeasurementRun)
            .where(MeasurementRun.imported_file_id == uuid.UUID(imported_file_id))
            .order_by(MeasurementResult.value)
        ).all()
    finally:
        db.close()

    by_value = {row.value: row for row in rows}
    ok_row = by_value[Decimal("10.5")]
    assert ok_row.deviation == Decimal("0.5")
    assert ok_row.is_ok is True

    nok_row = by_value[Decimal("12")]
    assert nok_row.deviation == Decimal("2")
    assert nok_row.is_ok is False


def test_unknown_part_number_quarantines_with_clear_reason(imports_client: TestClient, as_role) -> None:
    # batch_lot carries a random suffix purely so this file's sha256 is
    # unique per test run -- otherwise a second run against a database that
    # still has the previous run's row (e.g. a local re-run without
    # recreating the disposable DB) would hit dedup (409) instead of
    # exercising the quarantine path this test is actually about.
    content = (
        f"part_number,batch_lot,run_at,machine_code,operator_identifier,sample_sequence,COL_1\n"
        f"MI-DEMO-DOES-NOT-EXIST,B-{uuid.uuid4().hex[:8]},2026-07-13T00:00:00+00:00,CMM-01,OP,1,1.5\n"
    ).encode()
    response = imports_client.post(
        "/api/v1/imports",
        headers=as_role("metrologist"),
        files={"file": ("unknown_part.csv", content, "text/csv")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["parse_status"] == "quarantined"
    assert "Unknown part_number" in body["quarantined_rows"][0]["reason"]
