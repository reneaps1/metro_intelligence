"""IQ-F30 (D29): admin-only upload of converted datasets to an authorized private host.

Fictitious data only (converted in ``tmp_path`` from the synthetic long-signal export).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from app.api.v1.auth import router as auth_router
from app.api.v1.private_datasets import router as private_router
from app.api.v1.quality_analytics import router as quality_router
from app.connectors.long_signal_batch import convert
from app.core.config import get_settings
from app.core.private_data import authorized_private_host, private_data_allowed
from app.services import dataset_registry
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import DEMO_USERS, KNOWN_PASSWORD
from test_long_signal_batch import _mapping, export  # noqa: F401  (fixture re-export)

BASE = "/api/v1/private-datasets"
AUTH_REF = "Autorizacion escrita del cliente 2026-11-11"


@pytest.fixture(scope="session")
def client(auth_database: None) -> TestClient:
    app = FastAPI(title="IQ-F30 private datasets test app")
    app.include_router(auth_router)
    app.include_router(private_router, prefix="/api/v1")
    app.include_router(quality_router, prefix="/api/v1")
    return TestClient(app)


@pytest.fixture(scope="session")
def as_role(client: TestClient) -> Callable[[str], dict[str, str]]:
    cache: dict[str, dict[str, str]] = {}

    def _login(role: str) -> dict[str, str]:
        if role not in cache:
            r = client.post("/auth/login", data={"username": DEMO_USERS[role], "password": KNOWN_PASSWORD})
            assert r.status_code == 200, r.text
            cache[role] = {"Authorization": f"Bearer {r.json()['access_token']}"}
        return cache[role]

    return _login


@pytest.fixture
def converted(export: list[Path], tmp_path: Path) -> Path:  # noqa: F811
    out = tmp_path / "converted"
    convert(export, _mapping(), out, partitions=1)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    manifest["display"] = {"label": "MI-DEMO-PRIV", "line": "Línea demo privada"}
    (out / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return out


@pytest.fixture
def host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Callable[..., Path]]:
    settings = get_settings()
    root = tmp_path / "private-root"
    dataset_registry.reset_cache()

    def _set(**values: object) -> Path:
        for key, value in values.items():
            monkeypatch.setattr(settings, key, value)
        return root

    _set(
        app_edition="industrial",
        app_env="private-demo",
        cors_origins="https://demo-privado.example.org",
        demo_real_datasets_dir=str(root),
        demo_private_host_authorization=None,
        private_datasets_upload_enabled=False,
    )
    monkeypatch.setenv("RENDER", "true")
    yield _set
    dataset_registry.reset_cache()


def _files(folder: Path, pieces_bytes: bytes | None = None) -> dict[str, tuple[str, bytes]]:
    manifest = (folder / "manifest.json").read_bytes()
    pieces = pieces_bytes if pieces_bytes is not None else (folder / "pieces.csv.gz").read_bytes()
    return {"manifest": ("manifest.json", manifest), "pieces": ("pieces.csv.gz", pieces)}


def test_hidden_unless_authorized_and_enabled(client: TestClient, as_role, host, converted: Path) -> None:
    admin = as_role("admin")
    assert client.put(f"{BASE}/pieza-x", files=_files(converted), headers=admin).status_code == 404
    host(private_datasets_upload_enabled=True)
    assert client.put(f"{BASE}/pieza-x", files=_files(converted), headers=admin).status_code == 404
    host(demo_private_host_authorization="corto")
    assert client.put(f"{BASE}/pieza-x", files=_files(converted), headers=admin).status_code == 404
    host(demo_private_host_authorization=AUTH_REF, app_env="production")
    assert not authorized_private_host() and not private_data_allowed()
    assert client.put(f"{BASE}/pieza-x", files=_files(converted), headers=admin).status_code == 404


def test_admin_uploads_and_the_part_is_offered_on_the_authorized_host(
    client: TestClient, as_role, host, converted: Path
) -> None:
    root = host(demo_private_host_authorization=AUTH_REF, private_datasets_upload_enabled=True)
    assert private_data_allowed()  # despite the hosted-platform marker and a public origin
    assert client.put(f"{BASE}/pieza-x", files=_files(converted)).status_code == 401
    assert (
        client.put(f"{BASE}/pieza-x", files=_files(converted), headers=as_role("metrologist")).status_code
        == 403
    )

    r = client.put(f"{BASE}/pieza-x", files=_files(converted), headers=as_role("admin"))
    assert r.status_code == 200, r.text
    assert r.json()["id"] == "real-pieza-x" and r.json()["label"] == "MI-DEMO-PRIV"
    assert (root / "pieza-x" / "manifest.json").is_file()
    catalog = client.get("/api/v1/quality-analytics/catalog", headers=as_role("metrologist")).json()
    assert "real-pieza-x" in [i["id"] for i in catalog["items"]]
    detail = client.get("/api/v1/quality-analytics/datasets/real-pieza-x", headers=as_role("metrologist"))
    assert detail.status_code == 200 and detail.json()["source_type"] == "REAL"

    assert client.delete(f"{BASE}/pieza-x", headers=as_role("admin")).status_code == 204
    assert not (root / "pieza-x").exists()
    assert client.delete(f"{BASE}/pieza-x", headers=as_role("admin")).status_code == 404


def test_invalid_uploads_leave_nothing_behind(client: TestClient, as_role, host, converted: Path) -> None:
    root = host(demo_private_host_authorization=AUTH_REF, private_datasets_upload_enabled=True)
    admin = as_role("admin")
    broken = (converted / "pieces.csv.gz").read_bytes()[:-10]
    assert client.put(f"{BASE}/pieza-y", files=_files(converted, broken), headers=admin).status_code == 422
    bad_manifest = {"manifest": ("manifest.json", b"{not json"), "pieces": ("p.gz", b"x")}
    assert client.put(f"{BASE}/pieza-y", files=bad_manifest, headers=admin).status_code == 422
    assert client.put(f"{BASE}/dimensional", files=_files(converted), headers=admin).status_code == 422
    assert client.put(f"{BASE}/Bad_Slug", files=_files(converted), headers=admin).status_code == 422
    assert [p.name for p in root.iterdir()] == []


def test_upload_with_a_product_file(client: TestClient, as_role, host, converted: Path) -> None:
    root = host(demo_private_host_authorization=AUTH_REF, private_datasets_upload_enabled=True)
    admin = as_role("admin")
    product = {
        "format": "product-spec-v1",
        "product": {"name": "Conector demo", "part_number": "MI-DEMO-0042"},
        "characteristics": [{"variable": "x0", "lsl": 0.5, "usl": 1.5}],
    }
    files = {**_files(converted), "product": ("product.json", json.dumps(product).encode())}
    r = client.put(f"{BASE}/pieza-p", files=files, headers=admin)
    assert r.status_code == 200, r.text
    assert r.json()["label"] == "Conector demo (MI-DEMO-0042)"
    assert (root / "pieza-p" / "product.json").is_file()
    detail = client.get("/api/v1/quality-analytics/datasets/real-pieza-p", headers=admin).json()
    assert detail["product"]["part_number"] == "MI-DEMO-0042"
    assert detail["product"]["characteristics_with_limits"] == 1
    x0 = next(v for v in detail["variables"] if v["key"] == "x0")
    assert (x0["lsl"], x0["usl"]) == (0.5, 1.5)

    foreign = {**product, "characteristics": [{"variable": "nope", "usl": 1.0}]}
    files = {**_files(converted), "product": ("product.json", json.dumps(foreign).encode())}
    assert client.put(f"{BASE}/pieza-q", files=files, headers=admin).status_code == 422
    assert not (root / "pieza-q").exists()
