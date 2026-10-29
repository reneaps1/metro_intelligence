"""IQ-F6: /api/v1/quality-analytics imports (preview, dataset creation, ownership, sample)."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from app.api.v1.auth import router as auth_router
from app.api.v1.quality_analytics import router as quality_router
from app.api.v1.quality_imports import router as imports_router
from app.core.config import get_settings
from app.services.imported_dataset_store import get_imported_dataset_store
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import AUTH_DB_URL, DEMO_USERS, KNOWN_PASSWORD

BASE = "/api/v1/quality-analytics"
SAMPLES = Path(__file__).resolve().parents[2] / "seed" / "sample_files"
LONG = (SAMPLES / "mi_demo_dimensional_long.csv").read_bytes()
WIDE = (SAMPLES / "mi_demo_dimensional_wide.csv").read_bytes()

LONG_MAPPING = {
    "layout": "long",
    "delimiter": ";",
    "decimal": ",",
    "date_order": "dmy",
    "timestamp": "Fecha",
    "time": "Hora",
    "piece_id": "ID_Pieza",
    "group": "Ciclo",
    "cavity": "Nido",
    "machine": "Maquina",
    "shift": "Turno",
    "ok_nok": "Resultado",
    "variable": "Caracteristica",
    "value": "Valor",
    "lsl": "LIE",
    "usl": "LSE",
    "unit": "Unidad",
}
WIDE_MAPPING = {
    "layout": "wide",
    "delimiter": ",",
    "decimal": ".",
    "timestamp": "timestamp",
    "piece_id": "serial",
    "cavity": "cavity",
    "machine": "press",
    "shift": "shift",
    "batch": "material_lot",
    "ok_nok": "result",
    "value_columns": ["PinHeight", "PinPitch", "BodyLength", "WallThickness", "Warp"],
    "specs": {
        "PinHeight": {"nominal": 2.5, "lsl": 2.47, "usl": 2.53, "unit": "mm"},
        "WallThickness": {"nominal": 0.8, "lsl": 0.77, "usl": 0.83, "unit": "mm"},
    },
}


@pytest.fixture(scope="session")
def client(auth_database: None) -> TestClient:
    app = FastAPI(title="IQ-F6 quality imports test app")
    app.include_router(auth_router)
    app.include_router(quality_router, prefix="/api/v1")
    app.include_router(imports_router, prefix="/api/v1")
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

    _set(app_edition="industrial")
    get_imported_dataset_store().clear()
    yield _set
    get_imported_dataset_store().clear()


def _upload(
    client: TestClient, headers, content: bytes, mapping: dict, *, file_size: int | None = None, name="f.csv"
):
    return client.post(
        f"{BASE}/datasets",
        files={"file": (name, content, "text/csv")},
        data={"mapping": json.dumps(mapping), "file_size": str(file_size or len(content))},
        headers=headers,
    )


def test_metrology_edition_hides_imports(client: TestClient, as_role, industrial) -> None:
    industrial(app_edition="metrology")
    h = as_role("admin")
    preview = client.post(
        f"{BASE}/imports/preview",
        files={"file": ("f.csv", LONG, "text/csv")},
        data={"file_size": len(LONG)},
        headers=h,
    )
    assert preview.status_code == 404
    assert _upload(client, h, LONG, LONG_MAPPING).status_code == 404


def test_rbac_requires_import_permission(client: TestClient, as_role) -> None:
    files = {"file": ("f.csv", LONG, "text/csv")}
    assert (
        client.post(f"{BASE}/imports/preview", files=files, data={"file_size": len(LONG)}).status_code == 401
    )
    for role in ("viewer", "quality_engineer", "auditor"):
        r = client.post(
            f"{BASE}/imports/preview", files=files, data={"file_size": len(LONG)}, headers=as_role(role)
        )
        assert r.status_code == 403, role
    r = client.post(
        f"{BASE}/imports/preview", files=files, data={"file_size": len(LONG)}, headers=as_role("metrologist")
    )
    assert r.status_code == 200


def test_preview_detects_format_and_suggests_mapping(client: TestClient, as_role) -> None:
    r = client.post(
        f"{BASE}/imports/preview",
        files={"file": ("long.csv", LONG, "text/csv")},
        data={"file_size": len(LONG)},
        headers=as_role("metrologist"),
    )
    body = r.json()
    assert (body["delimiter"], body["decimal"], body["encoding"]) == (";", ",", "utf-8")
    assert body["suggestion"]["layout"] == "long"
    assert body["suggestion"]["roles"]["cavity"] == "Nido"
    assert len(body["rows"]) == 20
    assert body["limits"]["max_rows"] == get_settings().dimensional_import_max_rows


def test_preview_delimiter_override(client: TestClient, as_role) -> None:
    r = client.post(
        f"{BASE}/imports/preview",
        files={"file": ("long.csv", LONG, "text/csv")},
        data={"file_size": len(LONG), "delimiter": ","},
        headers=as_role("metrologist"),
    )
    assert r.status_code == 200 and r.json()["delimiter"] == ","


def test_preview_rejects_bad_files(client: TestClient, as_role) -> None:
    h = as_role("metrologist")
    for name, content in (
        ("x.xlsx", LONG),
        ("x.csv", b"MZ\x90\x00"),
        ("x.csv", b"a,b\n1,=cmd|' /C calc'!A1\n"),
    ):
        r = client.post(
            f"{BASE}/imports/preview", files={"file": (name, content)}, data={"file_size": 10}, headers=h
        )
        assert r.status_code == 422, name


def test_import_long_creates_a_private_dataset_that_changes_the_analytics(
    client: TestClient, as_role
) -> None:
    h = as_role("metrologist")
    r = _upload(client, h, LONG, LONG_MAPPING, name="long.csv")
    assert r.status_code == 201, r.text
    body = r.json()
    report, ds = body["report"], body["dataset"]
    assert report["rows_accepted"] == 5756 and report["rows_quarantined"] == 5
    assert {q["reason"] for q in report["quarantine_by_reason"]} >= {
        "Valor no numérico",
        "Duplicado (misma pieza y variable)",
    }
    assert report["sample"]["limited"] is False
    assert ds["source_type"] == "IMPORTED" and ds["pieces"] == 960 and ds["cavities"] == list(range(1, 17))
    assert ds["has_reported_verdict"] is True

    listed = [d["id"] for d in client.get(f"{BASE}/datasets", headers=h).json()["items"]]
    assert listed == ["demo-synthetic-dimensional", ds["id"]]

    demo = client.get(f"{BASE}/overview", headers=h).json()["summary"]
    imported = client.get(f"{BASE}/overview", params={"dataset": ds["id"]}, headers=h).json()
    s = imported["summary"]
    assert imported["source_type"] == "IMPORTED"
    assert s["pieces"] == 960 != demo["pieces"]
    assert s["worst_cavity"]["cavity"] == 11 != demo["worst_cavity"]["cavity"]
    assert {p["variable"] for p in imported["pareto"]} == {v["key"] for v in ds["variables"]}
    assert s["source_reported"]["source_only_nok"] > 0

    detail = client.get(
        f"{BASE}/variable", params={"dataset": ds["id"], "variable": "Diametro_Pin"}, headers=h
    ).json()
    assert detail["capability"]["cpk"] is not None and detail["spec"]["nominal"] is None

    # other users cannot see it
    other = as_role("admin")
    assert client.get(f"{BASE}/overview", params={"dataset": ds["id"]}, headers=other).status_code == 404
    assert len(client.get(f"{BASE}/datasets", headers=other).json()["items"]) == 1

    # audit trail: who imported what, and that nothing was persisted
    engine = sa.create_engine(AUTH_DB_URL)
    with engine.connect() as conn:
        after = conn.execute(
            sa.text(
                "SELECT after_state FROM security_audit_log WHERE action = 'dimensional_dataset_imported' "
                "ORDER BY created_at DESC, id DESC LIMIT 1"
            )
        ).scalar_one()
    engine.dispose()
    assert after["filename"] == "long.csv" and after["persisted"] is False

    assert client.delete(f"{BASE}/datasets/{ds['id']}", headers=other).status_code == 404
    assert client.delete(f"{BASE}/datasets/{ds['id']}", headers=h).status_code == 204
    assert client.get(f"{BASE}/overview", params={"dataset": ds["id"]}, headers=h).status_code == 404


def test_import_wide_with_typed_tolerances(client: TestClient, as_role) -> None:
    r = _upload(client, as_role("metrologist"), WIDE, WIDE_MAPPING)
    body = r.json()
    assert r.status_code == 201
    ds = body["dataset"]
    assert ds["pieces"] == 1197 and ds["cavities"] == list(range(1, 9))
    by_key = {v["key"]: v for v in ds["variables"]}
    assert by_key["PinHeight"]["nominal"] == 2.5 and by_key["PinHeight"]["usl"] == pytest.approx(2.53)
    assert by_key["Warp"]["usl"] is None  # not typed -> no tolerance
    s = client.get(f"{BASE}/overview", params={"dataset": ds["id"]}, headers=as_role("metrologist")).json()[
        "summary"
    ]
    assert s["variables_with_tolerance"] == 2 and s["nok_pieces"] > 0


def test_large_file_is_analysed_as_a_labelled_sample(client: TestClient, as_role, industrial) -> None:
    industrial(dimensional_import_max_rows=1000)
    r = _upload(client, as_role("metrologist"), LONG, LONG_MAPPING)
    sample = r.json()["report"]["sample"]
    assert sample["limited"] is True and sample["rows_read"] == 1000
    assert 10 < sample["approx_file_pct"] < 25

    # the browser only sends the head of a file that exceeds the byte cap
    industrial(dimensional_import_max_rows=200_000)
    head = LONG[: len(LONG) // 4]
    r = _upload(client, as_role("metrologist"), head, LONG_MAPPING, file_size=len(LONG))
    sample = r.json()["report"]["sample"]
    assert sample["limited"] is True and sample["approx_file_pct"] == pytest.approx(25, abs=1)
    assert r.json()["report"]["rows_quarantined"] <= 5  # the cut last line is dropped, not quarantined


def test_invalid_mappings_are_422(client: TestClient, as_role) -> None:
    h = as_role("metrologist")
    assert _upload(client, h, LONG, {**LONG_MAPPING, "value": "Nope"}).status_code == 422
    assert _upload(client, h, LONG, {**LONG_MAPPING, "layout": "sideways"}).status_code == 422
    bad = {**WIDE_MAPPING, "specs": {"PinHeight": {"lsl": 3, "usl": 2}}}
    assert _upload(client, h, WIDE, bad).status_code == 422
    r = client.post(
        f"{BASE}/datasets",
        files={"file": ("f.csv", LONG)},
        data={"mapping": "{", "file_size": "1"},
        headers=h,
    )
    assert r.status_code == 422


def test_mapping_that_rejects_every_row_returns_the_report_without_dataset(
    client: TestClient, as_role
) -> None:
    r = _upload(
        client,
        as_role("metrologist"),
        LONG,
        {**LONG_MAPPING, "timestamp": "Caracteristica", "variable": "Fecha", "time": None},
    )
    body = r.json()
    assert r.status_code == 201 and body["dataset"] is None
    assert body["report"]["quarantine_by_reason"][0]["reason"] == "Fecha/hora vacía o no reconocida"


def test_store_keeps_at_most_three_datasets_per_user(client: TestClient, as_role) -> None:
    h = as_role("metrologist")
    ids = [_upload(client, h, WIDE, WIDE_MAPPING).json()["dataset"]["id"] for _ in range(4)]
    listed = [d["id"] for d in client.get(f"{BASE}/datasets", headers=h).json()["items"][1:]]
    assert listed == list(reversed(ids[1:]))
