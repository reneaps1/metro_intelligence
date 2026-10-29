"""IQ-F14: line quality panel -- service slicing, moments and API (fictitious data only)."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime

import pytest
from app.api.v1 import line_panel as line_panel_api
from app.api.v1.auth import router as auth_router
from app.api.v1.line_panel import router as line_panel_router
from app.core.config import get_settings
from app.engines.quality_analytics.dataset import DimensionalDataset, Station, Variable
from app.services import line_panel_service as svc
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import DEMO_USERS, KNOWN_PASSWORD

BASE = "/api/v1/line-panel"
UTC_OFFSET_S = -5 * 3600
# 06:00 plant time on a fictitious day; one piece every 20 s (180 per hour).
T0 = datetime(2026, 1, 5, 11, 0, tzinfo=UTC).timestamp()
STEP = 20.0
N = 3000
STREAKS = ((10, 15), (885, 906), (2210, 2217))  # NOK streaks of 6, 22 and 8 pieces
NO_VERDICT = 50  # a piece whose verdict is missing (counts as OK)
HOUR = 3600.0
SHIFT = 8 * HOUR


def _is_nok(i: int) -> bool:
    return (i % 25 == 0 and i != NO_VERDICT) or any(a <= i <= b for a, b in STREAKS)


def _fake_real() -> DimensionalDataset:
    """3 nests, 4 mold cavities, 2 stations; NOK every 25th piece plus three streaks."""
    nok = [_is_nok(i) for i in range(N)]
    reported: list[bool | None] = list(nok)
    reported[NO_VERDICT] = None
    return DimensionalDataset(
        id="real-dimensional",
        name="Datos reales · Planta demo",
        description="ficticio",
        source_type="REAL",
        variables=(Variable("x1", "Valor 1", "", 0.0, None, None, nominal_given=False, station="st_a"),),
        timestamps=[T0 + STEP * i for i in range(N)],
        group_ids=list(range(N)),
        machines=[None] * N,
        cavities=[1 + i % 3 for i in range(N)],  # type: ignore[misc]
        shifts=[None] * N,
        batches=[None] * N,
        values={"x1": [0.0] * N},  # type: ignore[dict-item]
        reported_nok=reported,
        mold_cavities=[1 + i % 4 for i in range(N)],  # type: ignore[misc]
        stations=(Station("st_a", "Estación A"), Station("st_b", "Estación B")),
        station_nok={
            "st_a": [bad and i % 2 == 0 for i, bad in enumerate(nok)],  # type: ignore[misc]
            "st_b": [bad and i % 2 == 1 for i, bad in enumerate(nok)],  # type: ignore[misc]
        },
        flags=[0] * N,
        utc_offset_s=UTC_OFFSET_S,
        nok_basis="reported",
        has_groups=False,
    )


def _fake_two_machines() -> DimensionalDataset:
    """Two interleaved machines, 4 pieces per timestamp (2 per machine), spec basis."""
    n = 48
    bad = {2, 5, 6, 13}
    return DimensionalDataset(
        id="demo-two-machines",
        name="Dos máquinas ficticias",
        description="ficticio",
        source_type="SIMULATED",
        variables=(Variable("x", "X", "mm", 0.0, -1.0, 1.0),),
        timestamps=[T0 + 60 * (i // 4) for i in range(n)],
        group_ids=[i // 2 for i in range(n)],
        machines=["M-A", "M-A", "M-B", "M-B"] * 12,  # type: ignore[arg-type]
        cavities=[1, 2, 1, 2] * 12,  # type: ignore[arg-type]
        shifts=[None] * n,
        batches=[None] * n,
        values={"x": [2.0 if i in bad else 0.0 for i in range(n)]},  # type: ignore[dict-item]
    )


@pytest.fixture(autouse=True)
def fresh_cache() -> Iterator[None]:
    svc.reset_cache()
    yield
    svc.reset_cache()


# --------------------------------------------------------------------------- service: line + cache


def test_line_sequence_verdicts_and_cache() -> None:
    ds = _fake_real()
    panel = svc.line_panel(ds)
    line = panel.line
    assert panel.provenance == "REAL" and line.machine is None and len(line.timestamps) == N
    assert line.nok == [_is_nok(i) for i in range(N)] and line.nok[NO_VERDICT] is False
    assert line.stations[0] == "st_a" and line.stations[25] == "st_b" and line.stations[1] is None
    assert panel.evaluation.reference_nok_rate == pytest.approx(sum(line.nok) / N)
    assert svc.line_panel(ds) is panel  # cached
    assert svc.line_panel(_fake_real()) is not panel  # another dataset object (a reload) recomputes


def test_machine_filter_and_line_order() -> None:
    ds = _fake_two_machines()
    panel = svc.line_panel(ds)
    assert panel.provenance == "SIMULATED" and panel.line.machine == "M-A"  # first machine by default
    rows = [i for i in range(48) if ds.machines[i] == "M-A"]
    assert panel.line.timestamps == [ds.timestamps[i] for i in rows]
    assert panel.line.nests == [ds.cavities[i] for i in rows]  # dataset order within a timestamp
    assert panel.line.nok == [i in {5, 13} for i in rows]
    assert sum(svc.line_panel(ds, "M-B").line.nok) == 2  # pieces 2 and 6
    assert panel.line.mold_cavities is None
    with pytest.raises(svc.UnknownMachineError):
        svc.line_panel(ds, "M-C")
    assert svc.resolve_machine(_fake_real(), "anything") is None  # no machines: ignored


# --------------------------------------------------------------------------- service: replay windows


def test_replay_lead_relative_indices_shifts_and_baseline() -> None:
    ds = _fake_real()
    panel = svc.line_panel(ds)
    start = T0 + STEP * 1500  # 14:20 plant time
    r = svc.replay_window(panel, start, 60)
    assert r.lead == 600 and len(r.t) == 600 + 180  # 180 pieces in the hour
    assert r.t[0] == -600 * STEP and r.t[600] == 0.0 and r.t[-1] == 179 * STEP
    assert (r.start_ts, r.end_ts) == (start, start + 3600)
    for column in (r.nest, r.cavity, r.nok, r.station, r.run, r.rate, r.nest_ratio, r.cavity_worst):
        assert len(column) == len(r.t)
    state = panel.evaluation.state
    assert r.run == state.run[900:1680] and r.cavity_worst == state.cavity_worst[900:1680]
    assert r.nok == [_is_nok(i) for i in range(900, 1680)]
    assert r.station[0] == 0 and r.station[25] == 1 and r.station[7] == -1  # pieces 900, 925, 907

    # First lead piece = 11:00 plant time; the window ends at 15:20: two shifts.
    assert [(s.label, s.start_ts, s.end_ts) for s in r.shifts] == [
        ("06:00–14:00", T0, T0 + SHIFT),
        ("14:00–22:00", T0 + SHIFT, T0 + 2 * SHIFT),
    ]
    # Baseline: shift start (piece 0) up to, not including, the first lead piece (900).
    b = r.baseline
    rows = range(900)
    assert b.pieces == 900 and b.nok == sum(_is_nok(i) for i in rows)
    assert b.by_nest == [(g, 300, sum(_is_nok(i) for i in rows if 1 + i % 3 == g)) for g in (1, 2, 3)]
    assert b.by_cavity == [(g, 225, sum(_is_nok(i) for i in rows if 1 + i % 4 == g)) for g in (1, 2, 3, 4)]
    nok_rows = [i for i in rows if _is_nok(i)]
    assert b.by_station == [
        ("st_a", sum(i % 2 == 0 for i in nok_rows)),
        ("st_b", sum(i % 2 == 1 for i in nok_rows)),
    ]
    assert b.hours == [
        (T0 + h * HOUR, 180, sum(_is_nok(i) for i in range(180 * h, 180 * (h + 1)))) for h in range(5)
    ]

    # The 22-piece streak (885..906) was raised at 889, before the first lead piece (900).
    alarms = dict(r.alarms)
    streak = alarms["R1::889"]
    assert (streak.raised_index, streak.evidence_from_index, streak.cleared_index) == (-11, -15, 7)
    assert streak.peak == 22.0 and streak.raised_ts == T0 + STEP * 889
    # Exactly the events active at some returned piece.
    expected = {
        svc.alarm_id(a)
        for a in panel.evaluation.alarms
        if any(
            a.raised_index <= i and (a.cleared_index is None or i < a.cleared_index) for i in range(900, 1680)
        )
    }
    assert set(alarms) == expected


def test_replay_near_the_start_the_end_and_outside_the_data() -> None:
    panel = svc.line_panel(_fake_real())
    r = svc.replay_window(panel, T0 + STEP * 100, 5)
    assert r.lead == 100 and r.t[0] == -100 * STEP and len(r.t) == 100 + 15
    assert r.baseline.pieces == 0 and r.baseline.hours == [] and r.baseline.by_nest[0] == (1, 0, 0)
    first = svc.replay_window(panel, None, 5)  # default: the first piece
    assert first.start_ts == T0 and first.lead == 0 and first.t[0] == 0.0
    last = svc.replay_window(panel, T0 + STEP * (N - 1), 240)
    assert last.lead == 600 and len(last.t) == 601
    for start in (T0 - 1, T0 + STEP * N):
        with pytest.raises(svc.StartOutsideDataError):
            svc.replay_window(panel, start, 60)


def test_shift_helpers_in_plant_time() -> None:
    five_am = T0 - HOUR  # 05:00 plant time belongs to the 22:00 shift of the day before
    start = svc.shift_start(five_am, UTC_OFFSET_S)
    assert start == T0 - SHIFT and svc.shift_label(start, UTC_OFFSET_S) == "22:00–06:00"
    assert svc.shift_start(T0, UTC_OFFSET_S) == T0 and svc.shift_label(T0, UTC_OFFSET_S) == "06:00–14:00"
    assert svc.shift_start(T0 + SHIFT - 1, UTC_OFFSET_S) == T0


# --------------------------------------------------------------------------- service: moments


def test_moments_kinds_ordering_and_replay_starts() -> None:
    panel = svc.line_panel(_fake_real())
    ts = panel.line.timestamps
    moments = panel.moments
    kinds = [m.kind for m in moments]
    assert kinds == sorted(kinds, key=["stop", "attention", "normal"].index)

    stops = [m for m in moments if m.kind == "stop"]
    assert [(m.key, m.rule, m.peak) for m in stops] == [
        ("stop-1", "R1", 22.0),
        ("stop-2", "R1", 8.0),
        ("stop-3", "R1", 6.0),
    ]
    assert stops[0].label == "Racha de 22 NOK consecutivas" and stops[0].raised_ts == ts[889]
    assert stops[0].replay_start_ts == ts[889 - 150]  # REAL: 150 pieces before the event
    assert stops[2].replay_start_ts == ts[0]  # raised at piece 14: clamped to the data

    attention = [m for m in moments if m.kind == "attention"]
    events = sorted(
        (a for a in panel.evaluation.alarms if a.rule in ("R2", "R3")),
        key=lambda a: (-a.peak / a.limit, a.raised_index),
    )
    assert attention and [m.raised_ts for m in attention] == [a.raised_ts for a in events[:6]]
    assert all(m.rule in ("R2", "R3") for m in attention)

    normal = [m for m in moments if m.kind == "normal"]
    assert normal and [m.peak for m in normal] == sorted((m.peak for m in normal), reverse=True)
    for m in normal:
        begin = ts.index(m.raised_ts)
        length = int(m.peak)
        assert length >= 600 and m.label.startswith("Operación normal")
        assert m.replay_start_ts == ts[begin + length // 10]
        assert not any(
            a.priority <= 2 and a.raised_index < begin + length and (a.cleared_index or N) > begin
            for a in panel.evaluation.alarms
        )
    # SIMULATED data: 36 pieces before the event, calm stretches from 120 pieces.
    simulated = svc.find_moments("SIMULATED", ts, panel.evaluation)
    assert next(m for m in simulated if m.key == "stop-1").replay_start_ts == ts[889 - 36]


# --------------------------------------------------------------------------- API


@pytest.fixture(scope="session")
def client(auth_database: None) -> TestClient:
    app = FastAPI(title="IQ-F14 line panel test app")
    app.include_router(auth_router)
    app.include_router(line_panel_router, prefix="/api/v1")
    return TestClient(app)


@pytest.fixture(scope="session")
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
def industrial(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    settings = get_settings()

    def _set(**values: object) -> None:
        for key, value in values.items():
            monkeypatch.setattr(settings, key, value)

    _set(app_edition="industrial")
    monkeypatch.setattr(line_panel_api, "load_real_dataset", lambda: None)
    return _set


def test_auth_rbac_and_edition(client: TestClient, as_role, industrial) -> None:
    for path in ("moments", "replay"):
        assert client.get(f"{BASE}/{path}").status_code == 401
        assert client.get(f"{BASE}/{path}", headers=as_role("viewer")).status_code == 403
    industrial(app_edition="metrology")
    assert client.get(f"{BASE}/moments", headers=as_role("admin")).status_code == 404


def test_synthetic_moments_and_replay_shapes(client: TestClient, as_role, industrial) -> None:
    headers = as_role("quality_engineer")
    body = client.get(f"{BASE}/moments", headers=headers).json()
    assert body["dataset"] == "demo-synthetic-dimensional" and body["provenance"] == "SIMULATED"
    assert body["engine_name"] == "line_alarm_engine" and body["engine_version"] == "v1-experimental"
    assert body["utc_offset_minutes"] == 0 and body["pieces"] > 0 and body["start_ts"] < body["end_ts"]
    assert 0 < body["reference_nok_rate"] < 1
    assert {m["kind"] for m in body["moments"]} <= {"stop", "attention", "normal"}
    moment = body["moments"][0]
    fields = {"key", "kind", "rule", "key_group", "raised_ts", "peak", "label", "replay_start_ts"}
    assert set(moment) == fields

    params = {"start": moment["replay_start_ts"], "minutes": 30}
    replay = client.get(f"{BASE}/replay", params=params, headers=headers)
    assert replay.status_code == 200, replay.text
    r = replay.json()
    assert r["machine"] == "INY-01" and r["nok_basis"] == "spec" and r["provenance"] == "SIMULATED"
    # IQ-F20: the synthetic line also carries its 32 mold cavities.
    assert r["line"] == {"nests": list(range(1, 13)), "mold_cavities": 32, "stations": []}
    rules = r["rules"]
    assert rules["texts"]["R1"] == (
        "5 NOK consecutivas en la línea → parar la línea y segregar desde la primera NOK de la racha."
    )
    assert rules["rate_limit"] == pytest.approx(rules["rate_factor"] * rules["reference_nok_rate"], abs=1e-5)
    assert set(rules["texts"]) == {"R1", "R2", "R3", "R4"}
    n = len(r["pieces"]["t"])
    assert 0 < r["lead"] <= 600 and n > r["lead"]
    for group in ("pieces", "state"):
        assert all(len(column) == n for column in r[group].values()), group
    assert r["pieces"]["t"][0] < 0 <= r["pieces"]["t"][r["lead"]]
    assert set(r["pieces"]["station"]) == {-1} and set(r["pieces"]["cavity"]) <= set(range(1, 33))
    assert all(v in (0, 1) and not isinstance(v, bool) for v in r["pieces"]["nok"])
    assert r["window"]["end_ts"] - r["window"]["start_ts"] == 30 * 60
    assert r["shifts"] and r["shifts"][0]["label"] in {"06:00–14:00", "14:00–22:00", "22:00–06:00"}
    assert len(r["baseline"]["by_cavity"]) == 32 and r["baseline"]["by_station"] == []
    for alarm in r["alarms"]:
        assert alarm["id"].startswith(alarm["rule"] + ":")
        assert alarm["raised_index"] < n

    other = client.get(f"{BASE}/replay", params={**params, "machine": "INY-02"}, headers=headers).json()
    assert other["machine"] == "INY-02"


def test_validation_errors(client: TestClient, as_role, industrial) -> None:
    headers = as_role("metrologist")
    start = client.get(f"{BASE}/moments", headers=headers).json()["start_ts"]
    for params in (
        {"minutes": 4},
        {"minutes": 241},
        {"start": start - 1},
        {"start": start + 30 * 86_400},
        {"machine": "INY-09"},
    ):
        assert client.get(f"{BASE}/replay", params=params, headers=headers).status_code == 422, params
    assert client.get(f"{BASE}/moments", params={"machine": "INY-09"}, headers=headers).status_code == 422
    for path in ("moments", "replay"):
        for dataset in ("nope", "real-dimensional"):  # unknown / REAL not configured
            response = client.get(f"{BASE}/{path}", params={"dataset": dataset}, headers=headers)
            assert response.status_code == 404, (path, dataset)


def test_real_dataset_replay(
    client: TestClient, as_role, industrial, monkeypatch: pytest.MonkeyPatch
) -> None:
    ds = _fake_real()
    monkeypatch.setattr(line_panel_api, "load_real_dataset", lambda: ds)
    headers = as_role("auditor")
    params = {"dataset": "real-dimensional", "machine": "INY-01"}  # machine ignored without machines
    moments = client.get(f"{BASE}/moments", params=params, headers=headers).json()
    assert moments["provenance"] == "REAL" and moments["utc_offset_minutes"] == -300
    assert moments["pieces"] == N and moments["moments"][0]["key"] == "stop-1"
    replay = client.get(
        f"{BASE}/replay", params={**params, "start": T0 + STEP * 1500, "minutes": 60}, headers=headers
    ).json()
    assert replay["machine"] is None and replay["nok_basis"] == "reported"
    assert replay["line"] == {
        "nests": [1, 2, 3],
        "mold_cavities": 4,
        "stations": [{"key": "st_a", "name": "Estación A"}, {"key": "st_b", "name": "Estación B"}],
    }
    assert replay["lead"] == 600 and replay["baseline"]["pieces"] == 900
    assert [s["label"] for s in replay["shifts"]] == ["06:00–14:00", "14:00–22:00"]
    streak = next(a for a in replay["alarms"] if a["id"] == "R1::889")
    assert streak["raised_index"] == -11 and streak["evidence_from_index"] == -15
    assert streak["cleared_index"] == 7 and streak["peak"] == 22 and streak["limit"] == 5
    assert streak["nests"] == [1, 2, 3, 1, 2] and streak["station"] == "st_b"  # pieces 885..889
    assert replay["pieces"]["cavity"][:4] == [1, 2, 3, 4]  # piece 900 is in mold cavity 1
    assert any(v is not None for v in replay["state"]["cavity_rate"])
