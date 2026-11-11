"""IQ-F21: private dataset registry, runtime barriers, single resolver and catalog API.

Fictitious data only: the datasets are converted in ``tmp_path`` from the
synthetic long-signal export of `test_long_signal_batch` (CLAUDE.md §7, §20).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from app.api.v1.auth import router as auth_router
from app.api.v1.line_panel import router as line_panel_router
from app.api.v1.predictive import router as predictive_router
from app.api.v1.quality_analytics import router as quality_router
from app.connectors.long_signal_batch import convert
from app.connectors.pieces_file import read_pieces
from app.core.config import get_settings
from app.core.private_data import hosted_platform_detected, only_loopback_origins, private_data_allowed
from app.engines.quality_analytics.synthetic import SYNTHETIC_DATASET_ID
from app.engines.quality_analytics.twins import twin_ids
from app.services import dataset_cache, dataset_registry, real_dataset_service, real_predictive_service
from app.services.dataset_registry import DatasetNotFoundError
from app.services.real_predictive_service import TOTAL_TARGET, target_flags
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import DEMO_USERS, KNOWN_PASSWORD
from test_long_signal_batch import _mapping, export  # noqa: F401  (fixture re-export)

BASE = "/api/v1/quality-analytics"
LOOPBACK = "http://localhost:5173,http://127.0.0.1:5173"


# --------------------------------------------------------------------------- fixtures


def _convert_into(root: Path, slug: str, files: list[Path], **blocks: object) -> Path:
    folder = root / slug
    convert(files, _mapping(), folder, partitions=2)
    manifest_path = folder / "manifest.json"
    if blocks:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.update(blocks)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return folder


@pytest.fixture
def private_root(export: list[Path], tmp_path: Path) -> Path:  # noqa: F811
    root = tmp_path / "private-datasets"
    root.mkdir()
    _convert_into(
        root,
        "pieza-b",
        export,
        display={"label": "MI-DEMO-B1", "line": "Línea demo B", "order": 20},
        groups={"primary": {"label": "Cavidad", "prefix": "C"}},
        assumptions=["Hora según el reloj de la máquina."],
    )
    _convert_into(
        root,
        "pieza-a",
        export,
        display={"label": "MI-DEMO-A1", "line": "Línea demo A", "order": 10},
        groups={"primary": {"label": "Nido"}, "secondary": {"label": "Lado"}},
    )
    # Invalid entries: counted as omitted, never offered.
    (root / "Not_A_Slug").mkdir()
    (root / "dimensional").mkdir()
    broken = root / "broken"
    broken.mkdir()
    (broken / "manifest.json").write_text("{not json", encoding="utf-8")
    (root / "loose-file.txt").write_text("ignored", encoding="utf-8")
    return root


@pytest.fixture
def configure(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., None]]:
    settings = get_settings()
    for marker in ("RENDER", "RENDER_SERVICE_ID", "DYNO", "FLY_APP_NAME", "K_SERVICE"):
        monkeypatch.delenv(marker, raising=False)
    dataset_registry.reset_cache()
    real_dataset_service.reset_cache()
    real_predictive_service.reset_cache()

    def _set(**values: object) -> None:
        for key, value in values.items():
            monkeypatch.setattr(settings, key, value)

    _set(
        app_edition="industrial",
        app_env="development",
        cors_origins=LOOPBACK,
        demo_real_dataset_path=None,
        demo_real_spec_path=None,
        demo_real_datasets_dir=None,
        demo_real_datasets_max_loaded=2,
    )
    yield _set
    dataset_registry.reset_cache()
    real_dataset_service.reset_cache()
    real_predictive_service.reset_cache()


# --------------------------------------------------------------------------- runtime barriers


@pytest.mark.parametrize(
    ("origins", "expected"),
    [
        ("http://localhost:5173", True),
        ('["http://localhost:5173","http://127.0.0.1:3000"]', True),
        ("http://[::1]:5173, http://localhost", True),
        ("http://localhost:5173,https://demo.example.org", False),
        ('["https://demo.example.org"]', False),
        ("", False),
        ("*", False),
    ],
)
def test_only_loopback_origins(origins: str, expected: bool) -> None:
    assert only_loopback_origins(origins) is expected


def test_hosted_platform_markers() -> None:
    assert hosted_platform_detected({}) is False
    assert hosted_platform_detected({"RENDER": "true"}) is True
    assert hosted_platform_detected({"DYNO": "web.1"}) is True


def test_each_barrier_alone_closes_private_data(
    configure, private_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configure(demo_real_datasets_dir=str(private_root))
    assert private_data_allowed() and len(dataset_registry.scan().entries) == 2

    configure(app_env="production")
    assert dataset_registry.scan().entries == ()
    configure(app_env="development", cors_origins="https://demo.example.org")
    assert dataset_registry.scan().entries == ()
    configure(cors_origins=LOOPBACK)
    monkeypatch.setenv("RENDER", "true")
    assert dataset_registry.scan().entries == ()
    with pytest.raises(DatasetNotFoundError):
        dataset_registry.resolve("real-pieza-a")


def test_the_legacy_dataset_obeys_the_same_barriers(
    configure,
    export: list[Path],  # noqa: F811
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = tmp_path / "legacy"
    convert(export, _mapping(), out, partitions=1)
    configure(demo_real_dataset_path=str(out / "manifest.json"))
    assert real_dataset_service.load_real_dataset() is not None
    real_dataset_service.reset_cache()
    configure(cors_origins="https://demo.example.org")
    assert real_dataset_service.load_real_dataset() is None
    assert real_dataset_service.real_dataset_configured() is False
    configure(cors_origins=LOOPBACK)
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-x")
    assert real_dataset_service.load_real_dataset() is None


# --------------------------------------------------------------------------- registry


def test_catalog_from_manifests_only_and_invalid_folders_counted(configure, private_root: Path) -> None:
    configure(demo_real_datasets_dir=str(private_root))
    catalog = dataset_registry.scan()
    assert [e.id for e in catalog.entries] == ["real-pieza-a", "real-pieza-b"]  # display.order
    a, b = catalog.entries
    assert (a.label, a.line, a.group_labels) == (
        "MI-DEMO-A1",
        "Línea demo A",
        {"primary": "Nido", "secondary": "Lado"},
    )
    assert b.assumptions == ("Hora según el reloj de la máquina.",) and b.pieces > 0
    assert catalog.omitted == 3  # bad slug, reserved slug, broken manifest
    assert not dataset_registry.is_loaded(a.id) and not dataset_registry.is_loaded(b.id)


def test_missing_or_unset_root_offers_nothing(configure, tmp_path: Path) -> None:
    assert dataset_registry.scan().entries == ()
    configure(demo_real_datasets_dir=str(tmp_path / "does-not-exist"))
    assert dataset_registry.scan().entries == ()


def test_lazy_load_lru_eviction_and_forget(configure, private_root: Path) -> None:
    configure(demo_real_datasets_dir=str(private_root), demo_real_datasets_max_loaded=1)
    forgotten: list[str] = []
    dataset_cache.register(forgotten.append)

    a = dataset_registry.resolve("real-pieza-a")
    assert a.id == "real-pieza-a" and a.name == "MI-DEMO-A1" and a.source_type == "REAL"
    assert dataset_registry.resolve("real-pieza-a") is a  # cached
    b = dataset_registry.resolve("real-pieza-b")
    assert b.id == "real-pieza-b"
    assert not dataset_registry.is_loaded("real-pieza-a") and "real-pieza-a" in forgotten
    again = dataset_registry.resolve("real-pieza-a")
    assert again.id == "real-pieza-a" and again is not a


def test_derived_caches_never_serve_an_evicted_dataset(configure, private_root: Path) -> None:
    """Regression for caches keyed by id(): eviction drops every cached result of that dataset."""
    configure(demo_real_datasets_dir=str(private_root), demo_real_datasets_max_loaded=1)
    a = dataset_registry.resolve("real-pieza-a")
    target_flags(a, TOTAL_TARGET)
    assert any(k[0] == "real-pieza-a" for k in real_predictive_service._cache)
    dataset_registry.resolve("real-pieza-b")
    assert not any(k[0] == "real-pieza-a" for k in real_predictive_service._cache)


def test_reloaded_when_the_folder_changes(configure, private_root: Path) -> None:
    configure(demo_real_datasets_dir=str(private_root))
    first = dataset_registry.resolve("real-pieza-b")
    manifest_path = private_root / "pieza-b" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["display"]["label"] = "MI-DEMO-B2"
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    second = dataset_registry.resolve("real-pieza-b")
    assert second is not first and second.name == "MI-DEMO-B2"


def test_a_corrupted_pieces_file_is_not_offered_for_loading(configure, private_root: Path) -> None:
    configure(demo_real_datasets_dir=str(private_root))
    pieces = next((private_root / "pieza-a").glob("*.csv.gz"))
    pieces.write_bytes(pieces.read_bytes()[:-8])
    with pytest.raises(DatasetNotFoundError):
        dataset_registry.resolve("real-pieza-a")
    assert dataset_registry.resolve("real-pieza-b").id == "real-pieza-b"


def test_resolver_order_and_unknown_ids(configure, private_root: Path) -> None:
    configure(demo_real_datasets_dir=str(private_root))
    assert dataset_registry.resolve(SYNTHETIC_DATASET_ID).source_type == "SIMULATED"
    for unknown in ("real-dimensional", "real-nope", "real-../pieza-a", "import-123", "", "../etc"):
        with pytest.raises(DatasetNotFoundError):
            dataset_registry.resolve(unknown)


def test_reader_takes_provenance_from_the_caller(export: list[Path], tmp_path: Path) -> None:  # noqa: F811
    out = tmp_path / "twin"
    convert(export, _mapping(), out, partitions=1)
    ds = read_pieces(
        out / "manifest.json",
        dataset_id="demo-twin",
        name="Gemelo",
        description="",
        max_bytes=10**7,
        max_pieces=10**6,
        source_type="SIMULATED",
    )
    assert ds.source_type == "SIMULATED"


def test_old_manifests_without_the_new_blocks_still_load(configure, private_root: Path) -> None:
    manifest_path = private_root / "pieza-b" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for key in ("display", "groups", "assumptions"):
        manifest.pop(key, None)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    configure(demo_real_datasets_dir=str(private_root))
    entry = dataset_registry.entry("real-pieza-b")
    assert entry is not None and entry.label == "pieza-b" and entry.group_labels == {}


# --------------------------------------------------------------------------- API


@pytest.fixture(scope="session")
def registry_app(auth_database: None) -> FastAPI:
    app = FastAPI(title="IQ-F21 registry test app")
    app.include_router(auth_router)
    for router in (quality_router, predictive_router, line_panel_router):
        app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture(scope="session")
def client(registry_app: FastAPI) -> TestClient:
    return TestClient(registry_app)


@pytest.fixture(scope="session")
def headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login", data={"username": DEMO_USERS["metrologist"], "password": KNOWN_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_catalog_api_lists_without_loading(
    client: TestClient, headers: dict[str, str], configure, private_root: Path
) -> None:
    configure(demo_real_datasets_dir=str(private_root))
    body = client.get(f"{BASE}/catalog", headers=headers).json()
    ids = [i["id"] for i in body["items"]]
    assert ids == ["real-pieza-a", "real-pieza-b", SYNTHETIC_DATASET_ID, *twin_ids()]
    assert body["initial_id"] == "real-pieza-a" and body["omitted"] == 3
    first = body["items"][0]
    assert (first["label"], first["line"], first["source_type"], first["loaded"]) == (
        "MI-DEMO-A1",
        "Línea demo A",
        "REAL",
        False,
    )
    assert not dataset_registry.is_loaded("real-pieza-a")
    assert str(private_root) not in json.dumps(body)


def test_catalog_on_a_public_host_is_synthetic_only(
    client: TestClient,
    headers: dict[str, str],
    configure,
    private_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure(demo_real_datasets_dir=str(private_root))
    monkeypatch.setenv("RENDER", "true")
    body = client.get(f"{BASE}/catalog", headers=headers).json()
    assert [i["id"] for i in body["items"]] == [SYNTHETIC_DATASET_ID, *twin_ids()]
    assert all(i["source_type"] == "SIMULATED" for i in body["items"])
    assert body["initial_id"] == SYNTHETIC_DATASET_ID and body["omitted"] == 0
    assert client.get(f"{BASE}/datasets/real-pieza-a", headers=headers).status_code == 404


def test_dataset_detail_and_analytics_follow_the_selected_part(
    client: TestClient, headers: dict[str, str], configure, private_root: Path
) -> None:
    configure(demo_real_datasets_dir=str(private_root))
    detail = client.get(f"{BASE}/datasets/real-pieza-b", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["id"] == "real-pieza-b" and body["name"] == "MI-DEMO-B1" and body["line"] == "Línea demo B"
    assert body["group_labels"] == {"primary": "Cavidad"} and body["process_join"] is False
    assert body["assumptions"] == ["Hora según el reloj de la máquina."]
    assert dataset_registry.is_loaded("real-pieza-b")

    for dataset in ("real-pieza-a", "real-pieza-b"):
        overview = client.get(f"{BASE}/overview", params={"dataset": dataset}, headers=headers)
        assert overview.status_code == 200 and overview.json()["dataset_id"] == dataset
        moments = client.get("/api/v1/line-panel/moments", params={"dataset": dataset}, headers=headers)
        assert moments.status_code == 200, moments.text
        waves = client.get("/api/v1/predictive/nok-waves", params={"dataset": dataset}, headers=headers)
        assert waves.status_code == 200, waves.text

    assert client.get(f"{BASE}/datasets/real-nope", headers=headers).status_code == 404
    assert client.get(f"{BASE}/overview", params={"dataset": "real-nope"}, headers=headers).status_code == 404


def test_vista_a_is_opt_in_per_part(
    client: TestClient, headers: dict[str, str], configure, private_root: Path
) -> None:
    configure(demo_real_datasets_dir=str(private_root))
    response = client.get(
        f"{BASE}/process-join",
        params={"dataset": "real-pieza-a", "signal": "INY-01:mold_temp"},
        headers=headers,
    )
    assert response.status_code == 404


def test_private_blocks_are_per_part_and_never_borrowed(
    client: TestClient, headers: dict[str, str], configure, private_root: Path
) -> None:
    configure(demo_real_datasets_dir=str(private_root))
    summary = {
        "title": "Resumen ficticio de la pieza",
        "period": "Período ficticio",
        "records": 10,
        "piece_ids": 5,
        "variables": 3,
        "nok_definition": "Veredicto de la máquina.",
        "critical_nest": 1,
        "critical_nest_relative_risk": 2.0,
        "relative_risk_basis": "Ficticio.",
        "notes": [],
    }
    (private_root / "pieza-a" / "report-summary.json").write_text(json.dumps(summary), encoding="utf-8")

    own = client.get(f"{BASE}/report-summary", params={"dataset": "real-pieza-a"}, headers=headers)
    assert own.status_code == 200 and own.json()["illustrative"] is False
    assert own.json()["title"] == "Resumen ficticio de la pieza"
    assert (
        client.get(f"{BASE}/report-summary", params={"dataset": "real-pieza-b"}, headers=headers).status_code
        == 404
    )
    synthetic = client.get(
        f"{BASE}/report-summary", params={"dataset": SYNTHETIC_DATASET_ID}, headers=headers
    )
    assert synthetic.json()["illustrative"] is True
    legacy = client.get(f"{BASE}/report-summary", headers=headers)
    assert legacy.status_code == 200  # F5 behaviour without the parameter

    lab = client.get("/api/v1/predictive/model-lab", params={"dataset": "real-pieza-a"}, headers=headers)
    assert lab.status_code == 404
    lab_synthetic = client.get(
        "/api/v1/predictive/model-lab", params={"dataset": SYNTHETIC_DATASET_ID}, headers=headers
    )
    assert lab_synthetic.status_code == 200 and lab_synthetic.json()["illustrative"] is True
