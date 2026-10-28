"""IQ-F5: /api/v1/quality-analytics (edition gating, RBAC, filters, report summary)."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from app.api.v1.auth import router as auth_router
from app.api.v1.quality_analytics import router as quality_router
from app.core.config import get_settings
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import DEMO_USERS, KNOWN_PASSWORD

BASE = "/api/v1/quality-analytics"


@pytest.fixture(scope="session")
def quality_app(auth_database: None) -> FastAPI:
    app = FastAPI(title="IQ-F5 quality analytics test app")
    app.include_router(auth_router)
    app.include_router(quality_router, prefix="/api/v1")
    return app


@pytest.fixture(scope="session")
def client(quality_app: FastAPI) -> TestClient:
    return TestClient(quality_app)


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


@pytest.fixture
def settings_patch(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., None]]:
    settings = get_settings()

    def _set(**values: object) -> None:
        for key, value in values.items():
            monkeypatch.setattr(settings, key, value)

    _set(app_edition="industrial", demo_report_summary_path=None)
    yield _set


def test_metrology_edition_hides_quality_analytics(client: TestClient, as_role, settings_patch) -> None:
    settings_patch(app_edition="metrology")
    for path in ("/datasets", "/overview", "/variable?variable=PinsLength", "/report-summary"):
        assert client.get(BASE + path, headers=as_role("admin")).status_code == 404


def test_rbac(client: TestClient, as_role, settings_patch) -> None:
    assert client.get(f"{BASE}/datasets").status_code == 401
    assert client.get(f"{BASE}/datasets", headers=as_role("viewer")).status_code == 403
    for role in ("metrologist", "quality_engineer", "admin", "auditor"):
        assert client.get(f"{BASE}/datasets", headers=as_role(role)).status_code == 200


def test_datasets_describe_filters_and_mechanisms(client: TestClient, as_role, settings_patch) -> None:
    body = client.get(f"{BASE}/datasets", headers=as_role("metrologist")).json()
    ds = body["items"][0]
    assert ds["source_type"] == "SIMULATED"
    assert ds["available_filters"] == {
        "machine": True,
        "cavity": True,
        "shift": True,
        "batch": True,
        "mold_cavity": False,
        "station": False,
        "quality_flags": False,
    }
    assert len(ds["variables"]) == 10 and ds["cavities"] == list(range(1, 13))
    coplanarity = next(v for v in ds["variables"] if v["key"] == "Coplanarity")
    assert coplanarity["lsl"] is None and coplanarity["usl"] == pytest.approx(0.08)
    assert ds["mechanisms"]


def test_overview_filters_change_the_result(client: TestClient, as_role, settings_patch) -> None:
    h = as_role("metrologist")
    full = client.get(f"{BASE}/overview", headers=h).json()
    nest = client.get(f"{BASE}/overview", params={"cavities": "4"}, headers=h).json()
    day = client.get(
        f"{BASE}/overview",
        params={"start": "2026-10-14T00:00:00Z", "end": "2026-10-15T00:00:00Z", "machines": "INY-01"},
        headers=h,
    ).json()
    assert full["summary"]["pieces"] == 60_480
    assert nest["summary"]["pieces"] == 5_040
    assert nest["summary"]["nok_rate"] > full["summary"]["nok_rate"]
    assert day["summary"]["pieces"] == 360 * 12
    assert [b["bucket"] for b in day["trend"]] == ["2026-10-14"]
    hourly = client.get(f"{BASE}/overview", params={"granularity": "hour"}, headers=h).json()
    assert len(hourly["trend"]) == 7 * 24
    assert len(full["heatmap"]) == 12 * 10


@pytest.mark.parametrize(
    ("path", "params", "expected"),
    [
        ("/overview", {"dataset": "nope"}, 404),
        ("/overview", {"cavities": "a,b"}, 422),
        ("/overview", {"variables": "Nope"}, 422),
        ("/overview", {"granularity": "week"}, 422),
        ("/overview", {"start": "2026-10-14T00:00:00"}, 422),
        ("/variable", {"variable": "Nope"}, 404),
        ("/variable", {"variable": "PinsLength", "group_by": "color"}, 422),
    ],
)
def test_validation(
    client: TestClient, as_role, settings_patch, path: str, params: dict, expected: int
) -> None:
    assert client.get(BASE + path, params=params, headers=as_role("admin")).status_code == expected


def test_variable_detail_payload(client: TestClient, as_role, settings_patch) -> None:
    body = client.get(
        f"{BASE}/variable",
        params={"variable": "PinsLength", "group_by": "shift"},
        headers=as_role("metrologist"),
    ).json()
    assert body["spec"]["lsl"] == pytest.approx(11.95) and body["spec"]["usl"] == pytest.approx(12.05)
    assert body["control_limits"]["ucl"] != body["spec"]["usl"]
    assert body["capability"]["cpk"] is not None
    assert [g["group"] for g in body["groups"]] == ["A", "B", "C"]
    assert 0 < len(body["series"]) <= 1500 and body["series_thinned"] is True
    assert len(body["cpk_by_day"]) == 7


def test_report_summary_placeholder_is_flagged(client: TestClient, as_role, settings_patch) -> None:
    body = client.get(f"{BASE}/report-summary", headers=as_role("metrologist")).json()
    assert body["source"] == "placeholder" and body["illustrative"] is True


def test_report_summary_reads_private_file(
    client: TestClient, as_role, settings_patch, tmp_path: Path
) -> None:
    private = tmp_path / "summary.json"
    private.write_text(
        json.dumps(
            {
                "title": "Informe de prueba",
                "period": "1–2 ene",
                "records": 123,
                "nok_definition": "def",
                "critical_nest": 3,
                "critical_nest_relative_risk": 7.5,
                "illustrative": True,  # ignored: a private file is never illustrative
            }
        ),
        encoding="utf-8",
    )
    settings_patch(demo_report_summary_path=str(private))
    body = client.get(f"{BASE}/report-summary", headers=as_role("metrologist")).json()
    assert body["source"] == "private" and body["illustrative"] is False
    assert body["records"] == 123 and body["critical_nest"] == 3


def test_report_summary_bad_file_falls_back(
    client: TestClient, as_role, settings_patch, tmp_path: Path
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    settings_patch(demo_report_summary_path=str(bad))
    body = client.get(f"{BASE}/report-summary", headers=as_role("metrologist")).json()
    assert body["source"] == "placeholder"
    settings_patch(demo_report_summary_path=str(tmp_path / "missing.json"))
    assert (
        client.get(f"{BASE}/report-summary", headers=as_role("metrologist")).json()["source"] == "placeholder"
    )
