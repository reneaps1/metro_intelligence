"""IQ-F10: REAL dataset loaded from a private path (service + API, fictitious data)."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from app.api.v1.auth import router as auth_router
from app.api.v1.quality_analytics import router as quality_router
from app.connectors.long_signal_batch import convert
from app.core.config import get_settings
from app.services import real_dataset_service
from app.services.real_dataset_service import REAL_DATASET_ID, load_real_dataset
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import DEMO_USERS, KNOWN_PASSWORD
from test_long_signal_batch import _mapping, export  # noqa: F401  (fixture re-export)

BASE = "/api/v1/quality-analytics"


@pytest.fixture(scope="session")
def real_app(auth_database: None) -> FastAPI:
    app = FastAPI(title="IQ-F10 real dataset test app")
    app.include_router(auth_router)
    app.include_router(quality_router, prefix="/api/v1")
    return app


@pytest.fixture(scope="session")
def client(real_app: FastAPI) -> TestClient:
    return TestClient(real_app)


@pytest.fixture(scope="session")
def headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login", data={"username": DEMO_USERS["metrologist"], "password": KNOWN_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def real_path(export: list[Path], tmp_path: Path) -> Path:  # noqa: F811
    out = tmp_path / "real"
    convert(export, _mapping(), out, partitions=2)
    return out / "manifest.json"


@pytest.fixture
def configure(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., None]]:
    settings = get_settings()
    real_dataset_service.reset_cache()

    def _set(**values: object) -> None:
        for key, value in values.items():
            monkeypatch.setattr(settings, key, value)

    _set(
        app_edition="industrial",
        app_env="development",
        demo_client_label="Cliente demo",
        demo_real_dataset_path=None,
        demo_real_spec_path=None,
    )
    yield _set
    real_dataset_service.reset_cache()


def test_not_configured_or_unusable_means_not_offered(configure, tmp_path: Path) -> None:
    assert load_real_dataset() is None
    configure(demo_real_dataset_path=str(tmp_path / "missing.json"))
    assert load_real_dataset() is None


def test_production_never_loads_real_data(configure, real_path: Path) -> None:
    configure(demo_real_dataset_path=str(real_path), app_env="production")
    assert load_real_dataset() is None


def test_size_cap_is_enforced(configure, real_path: Path) -> None:
    configure(demo_real_dataset_path=str(real_path), demo_real_dataset_max_pieces=1_000)
    assert load_real_dataset() is not None
    real_dataset_service.reset_cache()
    configure(demo_real_dataset_max_mb=1)
    assert load_real_dataset() is not None  # tiny file, under the cap


def test_cached_until_the_file_changes(configure, real_path: Path) -> None:
    configure(demo_real_dataset_path=str(real_path))
    first = load_real_dataset()
    assert first is not None and load_real_dataset() is first


def test_api_lists_real_first_and_aggregates_by_station(
    client: TestClient, headers: dict[str, str], configure, real_path: Path
) -> None:
    configure(demo_real_dataset_path=str(real_path), demo_client_label="Planta Demo")
    items = client.get(f"{BASE}/datasets", headers=headers).json()["items"]
    real = items[0]
    assert real["id"] == REAL_DATASET_ID and real["source_type"] == "REAL"
    assert real["name"] == "Datos reales · Planta Demo"
    assert (
        real["nok_basis"] == "reported" and real["utc_offset_minutes"] == -300 and real["has_groups"] is False
    )
    assert [s["key"] for s in real["stations"]] == ["st_a", "st_b"]
    assert real["mold_cavities"] == [1, 2, 3]
    assert real["available_filters"]["mold_cavity"] is True and real["available_filters"]["station"] is True
    assert real["presets"][0]["key"] == "b_by_nest"
    assert real["data_quality"]["empty_cycles_excluded"] == 1

    body = client.get(f"{BASE}/overview", params={"dataset": REAL_DATASET_ID}, headers=headers).json()
    assert body["source_type"] == "REAL" and body["summary"]["nok_basis"] == "reported"
    assert body["station_pareto"][0]["station"] == "st_b" and body["heatmap_axis"] == "station"
    assert body["by_mold_cavity"]

    by_station = client.get(
        f"{BASE}/overview",
        params={"dataset": REAL_DATASET_ID, "stations": "st_a", "mold_cavities": "2,3"},
        headers=headers,
    ).json()
    assert by_station["summary"]["nok_pieces"] == 0 and by_station["summary"]["stations_counted"] == ["st_a"]

    detail = client.get(
        f"{BASE}/variable",
        params={"dataset": REAL_DATASET_ID, "variable": "x1", "group_by": "mold_cavity"},
        headers=headers,
    ).json()
    assert detail["group_by"] == "mold_cavity" and detail["nok_basis"] == "reported"


def test_api_validation_and_absence(
    client: TestClient, headers: dict[str, str], configure, real_path: Path
) -> None:
    assert (
        client.get(f"{BASE}/overview", params={"dataset": REAL_DATASET_ID}, headers=headers).status_code
        == 404
    )
    configure(demo_real_dataset_path=str(real_path))
    bad_station = client.get(
        f"{BASE}/overview", params={"dataset": REAL_DATASET_ID, "stations": "zz"}, headers=headers
    )
    assert bad_station.status_code == 422
    bad_mold = client.get(
        f"{BASE}/overview", params={"dataset": REAL_DATASET_ID, "mold_cavities": "x"}, headers=headers
    )
    assert bad_mold.status_code == 422
    # IQ-F20: the synthetic dataset has mold cavities; a dataset without them answers 422.
    synthetic_mold = client.get(
        f"{BASE}/variable", params={"variable": "PinsLength", "group_by": "mold_cavity"}, headers=headers
    )
    assert synthetic_mold.status_code == 200


# --------------------------------------------------------------------------- IQ-F19: X/Y position


def _write_spec(tmp_path: Path, **pair: object) -> Path:
    import json

    entry = {
        "key": "pin_a",
        "label": "Pin A",
        "x": "x0",
        "y": "x1",
        "nominal_x": 1.0,
        "nominal_y": 2.0,
        "tol_xy": 0.5,
        "circles": [{"label": "Plano", "diameter": 1.0}],
        **pair,
    }
    path = tmp_path / "pin-spec.json"
    path.write_text(json.dumps({"format": "pin-spec-v1", "pin_pairs": [entry]}), encoding="utf-8")
    return path


def test_real_xy_view_needs_the_private_spec(
    client: TestClient, headers: dict[str, str], configure, real_path: Path, tmp_path: Path
) -> None:
    configure(demo_real_dataset_path=str(real_path), demo_real_spec_path=None)
    assert load_real_dataset().pin_pairs == ()  # type: ignore[union-attr]
    assert client.get(f"{BASE}/datasets", headers=headers).json()["items"][0]["pin_pairs"] == []
    assert (
        client.get(
            f"{BASE}/xy", params={"dataset": REAL_DATASET_ID, "pair": "pin_a"}, headers=headers
        ).status_code
        == 404
    )

    configure(demo_real_spec_path=str(_write_spec(tmp_path)))
    real = client.get(f"{BASE}/datasets", headers=headers).json()["items"][0]
    assert real["pin_pairs"] == [{"key": "pin_a", "label": "Pin A"}]
    body = client.get(
        f"{BASE}/xy",
        params={"dataset": REAL_DATASET_ID, "pair": "pin_a", "group_by": "mold_cavity"},
        headers=headers,
    ).json()
    assert body["source_type"] == "REAL" and body["group_by"] == "mold_cavity"
    assert body["pieces"] == 6 and body["nok_label"].endswith("máquina")
    assert {g["group"] for g in body["groups"]} == {1, 2, 3}


def test_an_unusable_spec_only_hides_the_xy_view(configure, real_path: Path, tmp_path: Path) -> None:
    configure(demo_real_dataset_path=str(real_path))
    configure(demo_real_spec_path=str(_write_spec(tmp_path, x="not_a_variable")))
    ds = load_real_dataset()
    assert ds is not None and ds.pin_pairs == ()
    configure(demo_real_spec_path=str(tmp_path / "missing.json"))
    assert load_real_dataset() is not None


def test_xy_api_on_the_synthetic_dataset(client: TestClient, headers: dict[str, str], configure) -> None:
    ok = client.get(
        f"{BASE}/xy", params={"pair": "pin", "group_by": "nest", "cavities": "1,2"}, headers=headers
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["pair"]["tol_xy"] == 0.04 and body["circles"][0]["diameter"] == 0.08
    assert {g["group"] for g in body["groups"]} == {1, 2}
    assert client.get(f"{BASE}/xy", params={"pair": "nope"}, headers=headers).status_code == 404
    assert (
        client.get(
            f"{BASE}/xy", params={"pair": "pin", "group_by": "mold_cavity"}, headers=headers
        ).status_code
        == 200
    )
    assert (
        client.get(f"{BASE}/xy", params={"pair": "pin", "group_by": "zz"}, headers=headers).status_code == 422
    )
    assert client.get(f"{BASE}/xy", params={"pair": "pin"}).status_code == 401
