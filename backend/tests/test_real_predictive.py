"""IQ-F12: predictive lab over a REAL dataset -- engines, model lab studies and API (fictitious data)."""

from __future__ import annotations

import json
import random
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from app.api.v1 import predictive as predictive_api
from app.api.v1.auth import router as auth_router
from app.api.v1.predictive import router as predictive_router
from app.core.config import get_settings
from app.engines.experimental_ml.group_alarms import evaluate_group_alarms, longest_gap
from app.engines.experimental_ml.nok_waves import GroupPoint, retrospective_episodes
from app.engines.experimental_ml.piece_risk import past_features, roc_auc, run_risk_study, top_k
from app.engines.quality_analytics.dataset import DimensionalDataset, Station, Variable
from app.services import real_predictive_service
from app.services.model_lab_service import load_model_lab
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import DEMO_USERS, KNOWN_PASSWORD

BASE = "/api/v1/predictive"
DAY = 86_400.0
T0 = 1_767_600_000.0  # fictitious plant period


def _fake_real(n: int = 3_000, seed: int = 7) -> DimensionalDataset:
    """3 days, 4 mold cavities, 3 nests; cavity 2 degrades after a stop on day 1."""
    rng = random.Random(seed)
    ts: list[float] = []
    t = T0
    for i in range(n):
        t += 60 if i != n // 3 else 6 * 3600  # one long stop
        ts.append(t)
    mold = [1 + i % 4 for i in range(n)]
    nest = [1 + i % 3 for i in range(n)]
    st_a: list[bool | None] = []
    st_b: list[bool | None] = []
    for i in range(n):
        bad_cavity = mold[i] == 2 and i > n // 3
        st_a.append(rng.random() < (0.4 if bad_cavity else 0.01))
        st_b.append(rng.random() < 0.01)
    x = [rng.gauss(0, 1) for _ in range(n)]
    reported = [bool(a or b) for a, b in zip(st_a, st_b, strict=True)]
    return DimensionalDataset(
        id="real-dimensional",
        name="Datos reales · Planta demo",
        description="ficticio",
        source_type="REAL",
        variables=(Variable("x1", "Valor 1", "", 0.0, None, None, nominal_given=False, station="st_a"),),
        timestamps=ts,
        group_ids=list(range(n)),
        machines=[None] * n,
        cavities=nest,  # type: ignore[arg-type]
        shifts=[None] * n,
        batches=[None] * n,
        values={"x1": x},  # type: ignore[dict-item]
        reported_nok=reported,  # type: ignore[arg-type]
        mold_cavities=mold,  # type: ignore[arg-type]
        stations=(Station("st_a", "Estación A"), Station("st_b", "Estación B")),
        station_nok={"st_a": st_a, "st_b": st_b},
        flags=[0] * n,
        utc_offset_s=-5 * 3600,
        nok_basis="reported",
        has_groups=False,
    )


# --------------------------------------------------------------------------- engines


def test_group_alarm_rule_counts_before_and_after_the_first_alarm() -> None:
    ts = [float(i) for i in range(8)]
    groups = [1, 1, 1, 1, 1, 2, 1, 1]
    nok = [False, True, True, False, True, True, False, False]
    ev = evaluate_group_alarms(ts, groups, nok, k=2, n=3)
    g1 = next(g for g in ev.groups if g.group == 1)
    assert g1.first_alarm_ts == 2.0  # second NOK of group 1
    assert g1.nok == 3 and g1.nok_after_first_alarm == 2
    assert g1.ok_in_alarm == 1 and g1.nok_in_alarm == 2 and g1.alarm_runs == 1
    assert ev.groups_alarmed == 1
    since = evaluate_group_alarms(ts, groups, nok, k=2, n=3, since=3.0)
    assert since.pieces == 5
    assert longest_gap([0.0, 1.0, 10.0, 11.0]) == (1.0, 10.0)
    with pytest.raises(ValueError):
        evaluate_group_alarms(ts, groups, nok, k=4, n=3)


def test_retrospective_episodes_cover_the_whole_window() -> None:
    noks = [0] * 10 + [1, 1, 1] + [0] * 10
    series = [GroupPoint(float(i), 1, v) for i, v in enumerate(noks)]
    episodes = retrospective_episodes(series, window=4, threshold=2)
    assert len(episodes) == 1
    assert episodes[0].start == 8  # the window starting at 8 (8..11) already holds 2 NOK
    assert episodes[0].end == 11 + 3  # last in-wave start + window - 1


def test_roc_auc_and_top_k() -> None:
    assert roc_auc([0.9, 0.8, 0.2, 0.1], [1, 1, 0, 0]) == 1.0
    assert roc_auc([0.1, 0.2, 0.8, 0.9], [1, 1, 0, 0]) == 0.0
    assert roc_auc([0.5, 0.5, 0.5, 0.5], [1, 0, 1, 0]) == 0.5
    top = top_k([float(i) for i in range(100)], [1 if i >= 95 else 0 for i in range(100)])
    five = next(t for t in top if t.share == 0.05)
    assert (
        five.flagged == 5 and five.nok_caught == 5 and five.recall == 1.0 and five.lift == pytest.approx(20.0)
    )


def test_past_features_never_see_the_piece_itself() -> None:
    rows = past_features([1, 1, 1], [1, 1, 1], [True, True, False])
    assert rows[0] == [0.0, 0.0, 0.5, 0.0, 0.0]  # nothing seen yet (cumulative rate is smoothed)
    assert rows[1] is not None and rows[1][0] == 1.0  # only the first piece (NOK) is in the past
    assert past_features([None], [1], [True]) == [None]


def test_risk_study_trains_on_the_past_and_tests_on_the_last_day() -> None:
    ds = _fake_real()
    flags = [p == "st_a" for p in ds.primary_fail]
    study = run_risk_study(ds.timestamps, ds.mold_cavities, ds.cavities, flags, ds.utc_offset_s)  # type: ignore[arg-type]
    assert study.test_pieces > 0 and study.train_pieces > study.test_pieces
    assert study.test_day == "2026-01-07"  # last plant-local day of the fictitious period
    assert study.model.roc_auc > 0.8  # a degraded cavity is easy to rank from its own recent past
    assert [b.key for b in study.baselines] == ["cavity_rate", "alarm_rule"]
    assert study.alarm_rule is not None and 0 <= study.alarm_rule.share <= 1
    assert len(study.coefficients) == 5


# --------------------------------------------------------------------------- model lab: several studies


@pytest.fixture
def settings_patch(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., None]]:
    settings = get_settings()

    def _set(**values: object) -> None:
        for key, value in values.items():
            monkeypatch.setattr(settings, key, value)

    _set(app_edition="industrial", app_env="development")
    real_predictive_service.reset_cache()
    yield _set
    real_predictive_service.reset_cache()


def _study(title: str, tp: int, fp: int, fn: int, tn: int) -> dict[str, object]:
    return {
        "title": title,
        "study_date": "2026-01-08",
        "dataset_description": "ficticio",
        "split_description": "temporal",
        "models": [
            {
                "key": "m",
                "name": "Modelo",
                "family": "baseline",
                "roc_auc": 0.8,
                "pr_auc": 0.3,
                "recall": tp / (tp + fn),
                "precision": tp / (tp + fp),
                "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
            }
        ],
    }


def test_model_lab_accepts_several_studies(settings_patch, tmp_path: Path) -> None:
    path = tmp_path / "lab.json"
    path.write_text(json.dumps({"studies": [_study("A", 10, 10, 5, 75), _study("B", 3, 1, 1, 95)]}), "utf-8")
    settings_patch(demo_model_lab_path=str(path))
    lab = load_model_lab()
    assert lab.source == "private" and lab.title == "A"
    assert [s.title for s in lab.additional_studies] == ["B"]
    assert lab.additional_studies[0].test_n == 100
    path.write_text(json.dumps({"studies": []}), "utf-8")
    assert load_model_lab().source == "placeholder"


# --------------------------------------------------------------------------- API


@pytest.fixture(scope="session")
def client(auth_database: None) -> TestClient:
    app = FastAPI(title="IQ-F12 predictive test app")
    app.include_router(auth_router)
    app.include_router(predictive_router, prefix="/api/v1")
    return TestClient(app)


@pytest.fixture(scope="session")
def headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login", data={"username": DEMO_USERS["metrologist"], "password": KNOWN_PASSWORD}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def with_real(settings_patch, monkeypatch: pytest.MonkeyPatch) -> DimensionalDataset:
    ds = _fake_real()
    monkeypatch.setattr(predictive_api, "load_real_dataset", lambda: ds)
    return ds


def test_waves_and_cusum_run_on_the_real_dataset(client: TestClient, headers, with_real) -> None:
    params = {"dataset": "real-dimensional", "window": 30, "threshold": 6, "horizon": 30}
    body = client.get(f"{BASE}/nok-waves", params=params, headers=headers).json()
    assert body["source_type"] == "REAL" and body["episode_source"] == "retrospective"
    assert body["unit"] == "piezas" and body["utc_offset_minutes"] == -300
    assert body["summary"]["episodes"] >= 1 and "a posteriori" in body["episode_definition"]
    station = client.get(
        f"{BASE}/nok-waves", params={**params, "target": "station:st_b"}, headers=headers
    ).json()
    assert station["target"] == "station:st_b"
    cusum = client.get(
        f"{BASE}/cusum", params={"dataset": "real-dimensional", "series": "station:st_a"}, headers=headers
    )
    assert cusum.status_code == 200 and cusum.json()["series_label"].endswith("Estación A")


def test_group_alarms_and_piece_risk(client: TestClient, headers, with_real) -> None:
    alarms = client.get(f"{BASE}/group-alarms", params={"target": "station:st_a"}, headers=headers).json()
    assert alarms["scope"] == "after_longest_gap" and alarms["longest_gap"] is not None
    worst = alarms["groups"][0]
    assert worst["group"] == 2 and worst["first_alarm_ts"] is not None
    assert alarms["share_after_first_alarm"] > 0.5
    risk = client.get(f"{BASE}/piece-risk", params={"target": "station:st_a"}, headers=headers).json()
    assert risk["source_type"] == "REAL" and risk["model"]["roc_auc"] > 0.8
    assert {b["key"] for b in risk["baselines"]} == {"cavity_rate", "alarm_rule"}
    assert isinstance(risk["beats_baselines"], bool) and risk["hours"]


def test_validation_and_absence(
    client: TestClient, headers, settings_patch, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(predictive_api, "load_real_dataset", lambda: None)
    assert client.get(f"{BASE}/group-alarms", headers=headers).status_code == 404
    assert (
        client.get(f"{BASE}/nok-waves", params={"dataset": "real-dimensional"}, headers=headers).status_code
        == 404
    )
    # Synthetic keeps its F7 limits; REAL-only studies refuse the synthetic dataset.
    assert client.get(f"{BASE}/nok-waves", params={"window": 100}, headers=headers).status_code == 422
    synthetic = client.get(
        f"{BASE}/piece-risk", params={"dataset": "demo-synthetic-dimensional"}, headers=headers
    )
    assert synthetic.status_code == 422
    ds = _fake_real()
    monkeypatch.setattr(predictive_api, "load_real_dataset", lambda: ds)
    assert (
        client.get(f"{BASE}/piece-risk", params={"target": "station:zz"}, headers=headers).status_code == 422
    )
    assert client.get(f"{BASE}/group-alarms", params={"k": 10, "n": 5}, headers=headers).status_code == 422
