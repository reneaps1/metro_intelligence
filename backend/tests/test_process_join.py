"""IQ-F13 "Vista A": time join engine, service and /quality-analytics/process-join (fictitious data)."""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Iterator

import pytest
from app.api.v1 import quality_analytics as quality_api
from app.api.v1.auth import router as auth_router
from app.api.v1.quality_analytics import router as quality_router
from app.core.config import get_settings
from app.engines.process_simulation.alignment import cycle_feature
from app.engines.process_simulation.catalog import get_signal
from app.engines.process_simulation.generator import build_timeline, scenario_start
from app.engines.quality_analytics.dataset import DimensionalDataset, Station, Variable
from app.engines.quality_analytics.process_join import (
    JoinLagScore,
    best_lag,
    cycle_sums,
    join_at_lag,
    lag_scan,
    piece_counts,
)
from app.services import process_join_service, real_predictive_service
from app.services.process_join_service import CAUSAL_NOTE, CONTROL_NOTE, ILLUSTRATIVE_NOTE
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import DEMO_USERS, KNOWN_PASSWORD

BASE = "/api/v1/quality-analytics/process-join"
MOLD = "L1.INY-01.mold_temp"
HOLD = "L1.INY-01.holding_pressure"
B = 1800  # 30 min buckets
T0 = 1_767_603_600  # fictitious plant period, a whole UTC hour
OFFSET = -5 * 3600


# --------------------------------------------------------------------------- engine


def _at(bucket: int, k: int = 0) -> float:
    """A timestamp inside plant-time bucket ``bucket`` (relative to T0)."""
    return float(T0 + bucket * B + k)


def test_buckets_pair_pieces_with_the_cycles_starting_in_the_lagged_window() -> None:
    piece_ts: list[float] = []
    nok: list[bool] = []
    for bucket, count, bad in ((0, 60, 6), (1, 60, 12), (2, 49, 10), (3, 50, 25)):
        piece_ts += [_at(bucket, k) for k in range(count)]
        nok += [k < bad for k in range(count)]
    cycle_ts: list[float] = []
    values: list[float] = []
    for bucket, vals in ((-1, [7.0] * 5), (0, [1.0, 2.0, 3.0, 4.0, 5.0]), (1, [9.0] * 4), (2, [4.0] * 6)):
        cycle_ts += [_at(bucket, 10 * k) for k in range(len(vals))]
        values += vals
    # A cycle starting exactly on a bucket boundary belongs to the new bucket.
    cycle_ts += [_at(3, 0)] * 5
    values += [10.0] * 5

    pieces = piece_counts(piece_ts, nok, B, OFFSET)
    cycles = cycle_sums(cycle_ts, values, B, OFFSET)
    base = (T0 + OFFSET) // B  # plant-time index of bucket 0 (T0 and the offset are whole buckets)
    assert pieces[base] == (60, 6) and cycles[base + 3] == (50.0, 5)

    same = join_at_lag(pieces, cycles, 0, B, OFFSET)
    # Bucket 1: only 4 cycles; bucket 2: only 49 pieces.
    assert [(b.start_ts, b.x, b.y, b.pieces, b.cycles) for b in same.buckets] == [
        (_at(0), 3.0, 0.1, 60, 5),
        (_at(3), 10.0, 0.5, 50, 5),
    ]
    # Lag of one bucket: x comes from the cycles that started 30 min before the inspections.
    lagged = join_at_lag(pieces, cycles, 1, B, OFFSET)
    assert [(b.start_ts, b.x, b.cycles) for b in lagged.buckets] == [
        (_at(0), 7.0, 5),
        (_at(1), 3.0, 5),
        (_at(3), 4.0, 6),
    ]
    assert lagged.fit.n == 3


def _shifted_series(
    shift: int, buckets: int = 30
) -> tuple[dict[int, tuple[int, int]], dict[int, tuple[float, int]]]:
    rng = random.Random(3)
    x = {b: rng.uniform(0.0, 10.0) for b in range(-10, buckets)}
    cycles = {b: (v * 6, 6) for b, v in x.items()}
    pieces = {b: (100, round(2 * x[b - shift] + rng.uniform(0, 3))) for b in range(buckets)}
    return pieces, cycles


def test_lag_scan_finds_the_process_lead() -> None:
    pieces, cycles = _shifted_series(shift=2)
    scan = lag_scan(pieces, cycles, range(-6, 7), B, 0)
    assert [s.lag_buckets for s in scan] == list(range(-6, 7))
    assert best_lag(scan) == 2
    peak = next(s for s in scan if s.lag_buckets == 2)
    assert peak.r is not None and peak.r > 0.95 and peak.n == 30


def test_best_lag_needs_ten_buckets() -> None:
    assert best_lag([JoinLagScore(0, 9, 0.9), JoinLagScore(1, 10, 0.2), JoinLagScore(-1, 10, -0.3)]) == -1
    assert best_lag([JoinLagScore(0, 9, 0.9), JoinLagScore(1, 30, None)]) is None
    # Ties go to the smallest |lag|.
    assert best_lag([JoinLagScore(-2, 12, 0.5), JoinLagScore(1, 12, -0.5)]) == 1


# --------------------------------------------------------------------------- fictitious REAL dataset


def _fake_real(seed: int = 11) -> DimensionalDataset:
    """~9 h of pieces every 2 s with a 1 h stop and an NOK wave of a few hours; 6 nests, 2 stations."""
    rng = random.Random(seed)
    ts: list[float] = []
    t = float(T0 + 7)
    for i in range(15_000):
        t += 3600.0 if i == 6_000 else 2.0
        ts.append(t)
    st_a: list[bool | None] = []
    st_b: list[bool | None] = []
    for x in ts:
        hours = (x - T0) / 3600
        st_a.append(rng.random() < 0.02 + 0.08 * math.exp(-(((hours - 5.0) / 1.2) ** 2)))
        st_b.append(rng.random() < 0.01)
    n = len(ts)
    return DimensionalDataset(
        id="real-dimensional",
        name="Datos reales · Planta demo",
        description="ficticio",
        source_type="REAL",
        variables=(Variable("x1", "Valor 1", "", 0.0, None, None, nominal_given=False, station="st_a"),),
        timestamps=ts,
        group_ids=list(range(n)),
        machines=[None] * n,
        cavities=[1 + i % 6 for i in range(n)],  # type: ignore[misc]
        shifts=[None] * n,
        batches=[None] * n,
        values={"x1": [rng.gauss(0, 1) for _ in range(n)]},  # type: ignore[dict-item]
        reported_nok=[bool(a or b) for a, b in zip(st_a, st_b, strict=True)],  # type: ignore[arg-type]
        stations=(Station("st_a", "Estación A"), Station("st_b", "Estación B")),
        station_nok={"st_a": st_a, "st_b": st_b},
        utc_offset_s=OFFSET,
        nok_basis="reported",
        has_groups=False,
    )


@pytest.fixture(scope="module")
def real() -> DimensionalDataset:
    return _fake_real()


@pytest.fixture
def settings_patch(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., None]]:
    settings = get_settings()

    def _set(**values: object) -> None:
        for key, value in values.items():
            monkeypatch.setattr(settings, key, value)

    _set(app_edition="industrial", app_env="development")
    process_join_service.reset_cache()
    real_predictive_service.reset_cache()
    yield _set
    process_join_service.reset_cache()
    real_predictive_service.reset_cache()


def test_service_builds_and_caches_the_calendar_per_dataset(settings_patch, real) -> None:
    scenario = process_join_service.calendar_scenario(real)
    assert scenario is process_join_service.calendar_scenario(real)
    assert scenario.id == "real_calendar" and scenario.quality_driven and scenario.nest_count == 6
    assert len(scenario.downtimes) == 1
    other = _fake_real(seed=12)
    assert process_join_service.calendar_scenario(other) is not scenario


def test_service_bucket_values_match_the_raw_pieces_and_cycles(settings_patch, real) -> None:
    lag = 30
    result = process_join_service.process_join(real, MOLD, "station:st_a", 30, lag)
    timeline = build_timeline(result.scenario, "INY-01")
    origin = scenario_start(result.scenario).timestamp()
    signal = get_signal("mold_temp")
    bucket = result.join.buckets[len(result.join.buckets) // 2]
    start = bucket.start_ts
    in_window = [i for i, ts in enumerate(real.timestamps) if start <= ts < start + B]
    # Target ``station:st_a`` = pieces whose first failing station is st_a.
    first_fail = [real.primary_fail[i] == "st_a" for i in in_window]
    assert bucket.pieces == len(in_window) and bucket.y == pytest.approx(sum(first_fail) / len(in_window))
    lo, hi = start - lag * 60, start - lag * 60 + B
    values = [cycle_feature(timeline, signal, c) for c in timeline.cycles if lo <= origin + c.start < hi]
    assert bucket.cycles == len(values) and bucket.x == pytest.approx(sum(values) / len(values))
    assert all(b.pieces >= 50 and b.cycles >= 5 for b in result.join.buckets)


# --------------------------------------------------------------------------- API


@pytest.fixture(scope="module")
def client(auth_database: None) -> TestClient:
    app = FastAPI(title="IQ-F13 process join test app")
    app.include_router(auth_router)
    app.include_router(quality_router, prefix="/api/v1")
    return TestClient(app)


@pytest.fixture(scope="module")
def as_role(client: TestClient) -> Callable[[str], dict[str, str]]:
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
def with_real(settings_patch, monkeypatch: pytest.MonkeyPatch, real) -> DimensionalDataset:
    monkeypatch.setattr(quality_api, "load_real_dataset", lambda: real)
    return real


def test_mold_temperature_join_is_flagged_as_imposed(client: TestClient, as_role, with_real) -> None:
    response = client.get(BASE, params={"signal": MOLD}, headers=as_role("metrologist"))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["dataset"] == "real-dimensional" and body["scenario_id"] == "real_calendar"
    assert body["generator_version"] == "process-sim-1.2.0"
    assert body["signal"] == {"id": MOLD, "name": "Temperatura de molde (media por ciclo)", "unit": "°C"}
    assert body["target"] == "total" and body["target_label"] == "Resultado total de la máquina"
    assert (body["bucket_minutes"], body["lag_minutes"], body["utc_offset_minutes"]) == (30, 0, -300)
    assert body["provenance"] == ["REAL", "SIMULATED", "EXPERIMENTAL"]
    assert body["causal_imposed"] is True and body["notes"] == [ILLUSTRATIVE_NOTE, CAUSAL_NOTE]
    starts = [b["start_ts"] for b in body["buckets"]]
    assert starts == sorted(starts) and body["n"] == len(starts) >= 10
    assert all(b["pieces"] >= 50 and b["cycles"] >= 5 for b in body["buckets"])
    assert body["pearson_r"] > 0.5 and body["r_squared"] == pytest.approx(body["pearson_r"] ** 2)
    assert [s["lag_minutes"] for s in body["lag_scan"]] == list(range(-180, 181, 30))
    assert body["best_lag_minutes"] in {s["lag_minutes"] for s in body["lag_scan"]}


def test_other_signals_are_controls(client: TestClient, as_role, with_real) -> None:
    params = {"signal": HOLD, "target": "station:st_a", "bucket_minutes": 15, "lag_minutes": -45}
    body = client.get(BASE, params=params, headers=as_role("quality_engineer")).json()
    assert body["causal_imposed"] is False and body["notes"] == [ILLUSTRATIVE_NOTE, CONTROL_NOTE]
    assert body["target_label"].endswith("Estación A") and body["lag_minutes"] == -45
    assert [s["lag_minutes"] for s in body["lag_scan"]] == list(range(-180, 181, 15))
    peak = client.get(
        BASE, params={"signal": "L1.INY-01.injection_pressure"}, headers=as_role("admin")
    ).json()
    assert peak["causal_imposed"] is False and peak["signal"]["name"].endswith("(pico por ciclo)")
    assert abs(peak["pearson_r"] or 0.0) < 0.5


@pytest.mark.parametrize(
    "params",
    [
        {"signal": "L1.INY-01.nope"},
        {"signal": "L1.INY-02.mold_temp"},  # the calendar scenario runs on the primary machine
        {"signal": "L1.INY-01.dim_nok"},  # Vista B synthetic quality is not a process signal
        {"signal": "L1.INY-01.ambient_humidity"},
        {"signal": MOLD, "target": "station:zz"},
        {"signal": MOLD, "bucket_minutes": 20},
        {"signal": MOLD, "bucket_minutes": 30, "lag_minutes": 45},
        {"signal": MOLD, "bucket_minutes": 60, "lag_minutes": 240},
        {"signal": MOLD, "lag_minutes": "abc"},
        {},
    ],
)
def test_validation(client: TestClient, as_role, with_real, params: dict[str, object]) -> None:
    assert client.get(BASE, params=params, headers=as_role("metrologist")).status_code == 422


def test_unknown_dataset_or_real_absent_is_404(
    client: TestClient, as_role, settings_patch, monkeypatch: pytest.MonkeyPatch, real
) -> None:
    headers = as_role("metrologist")
    monkeypatch.setattr(quality_api, "load_real_dataset", lambda: None)
    assert client.get(BASE, params={"signal": MOLD}, headers=headers).status_code == 404
    monkeypatch.setattr(quality_api, "load_real_dataset", lambda: real)
    for dataset in ("demo-synthetic-dimensional", "nope"):
        response = client.get(BASE, params={"signal": MOLD, "dataset": dataset}, headers=headers)
        assert response.status_code == 404


def test_auth_rbac_and_edition(
    client: TestClient, as_role, settings_patch, monkeypatch: pytest.MonkeyPatch, real
) -> None:
    monkeypatch.setattr(quality_api, "load_real_dataset", lambda: real)
    params = {"signal": HOLD}
    assert client.get(BASE, params=params).status_code == 401
    assert client.get(BASE, params=params, headers=as_role("viewer")).status_code == 403
    assert client.get(BASE, params=params, headers=as_role("auditor")).status_code == 200
    settings_patch(app_edition="metrology")
    assert client.get(BASE, params=params, headers=as_role("admin")).status_code == 404
