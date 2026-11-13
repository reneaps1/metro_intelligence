"""Process API on a synthetic line loaded through the real ingest path."""

from __future__ import annotations

from datetime import datetime

import pytest
from app.api.v1.auth import router as auth_router
from app.api.v1.process import router as process_router
from app.core.database import engine as app_engine
from app.ingest.loader import LineLoader
from app.ingest.setup import ensure_catalog
from app.ingest.specs import import_specifications, parse_spec_file
from app.ingest.stats import build_daily_stats
from app.services.domain_purge import truncate_domain_tables
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from conftest import DEMO_USERS, KNOWN_PASSWORD
from line_csv_factory import LineFiles, Piece, make_config

DAY = "2026-03-02"
SPECS = {
    "source": "MI-DEMO drawing rev A",
    "valid_from": "2025-01-01T00:00:00Z",
    "specifications": [
        {"station": "LEN-CON", "measure": "pin", "nominal": 5.5, "lower_tol": -0.3, "upper_tol": 0.3},
        {"station": "POS-CON", "measure": "pin_x", "nominal": 0.0, "upper_tol": 0.30},
        {"station": "POS-CON", "measure": "pin_y", "nominal": 0.0, "upper_tol": 0.30},
    ],
}


@pytest.fixture(scope="module")
def line(auth_database: None, tmp_path_factory: pytest.TempPathFactory):
    # The auth DB is shared across test modules: start from empty domain tables.
    with app_engine.begin() as conn:
        truncate_domain_tables(conn)
    config = make_config()
    data_dir = tmp_path_factory.mktemp("line")
    LineFiles(
        day=DAY,
        pieces=[
            Piece("900001", recipe=2, nest=1, second=10),
            Piece("900002", recipe=3, nest=2, second=20, pos_con=0.35),
            Piece("900003", recipe=1, nest=3, second=30),
        ],
    ).write(data_dir)
    with Session(app_engine) as session:
        catalog = ensure_catalog(session, config, datetime(2026, 1, 1, tzinfo=config.timezone))
        import_specifications(session, config, catalog, parse_spec_file(SPECS))
        session.commit()
    loader = LineLoader(app_engine, config, catalog, data_dir, storage=None, raw_bucket="")
    loader.scan_recipes()
    loader.load_state()
    loader.load()
    build_daily_stats(app_engine, catalog.line_id, config.timezone.key)
    return catalog


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(process_router, prefix="/api/v1")
    return TestClient(app)


@pytest.fixture(scope="module")
def viewer(client: TestClient) -> dict[str, str]:
    response = client.post("/auth/login", data={"username": DEMO_USERS["viewer"], "password": KNOWN_PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_unauthenticated_is_rejected(client: TestClient, line) -> None:
    assert client.get("/api/v1/process/lines").status_code == 401
    assert client.get(f"/api/v1/process/lines/{line.line_id}/overview").status_code == 401


def test_lines_list_operations_in_sequence(client: TestClient, viewer, line) -> None:
    lines = client.get("/api/v1/process/lines", headers=viewer).json()
    ours = next(item for item in lines if item["id"] == str(line.line_id))
    assert [op["code"] for op in ours["operations"]] == [
        "ET1",
        "LEN-PCB",
        "LEN-CON",
        "POS-PCB",
        "POS-CON",
        "TYPE",
    ]


def test_overview_counts_and_recipe_filter(client: TestClient, viewer, line) -> None:
    body = client.get(
        f"/api/v1/process/lines/{line.line_id}/overview", params={"from": DAY, "to": DAY}, headers=viewer
    ).json()
    steps = {step["operation"]["code"]: step for step in body["steps"]}
    assert body["reference_pieces"] == 2  # recipe 1 is out of scope
    assert steps["TYPE"]["pieces"] == 2 and steps["TYPE"]["has_specification"] is False
    assert steps["TYPE"]["last_day"] == DAY

    # Every station logs both pieces here, so none is partial and all count
    # in the rolled yield: the product of each step's pass rate.
    assert not any(step["partial_logging"] for step in body["steps"])
    expected = 1.0
    for step in body["steps"]:
        rate = step["spec_nok_rate"] if step["has_specification"] else step["machine_nok_rate"]
        expected *= 1 - rate
    assert body["rolled_yield_steps"] == len(body["steps"])
    assert body["rolled_yield"] == pytest.approx(expected) and body["rolled_yield"] < 1

    # A range without data still says when the step last had data.
    empty = client.get(
        f"/api/v1/process/lines/{line.line_id}/overview",
        params={"from": "2026-04-01", "to": "2026-04-02"},
        headers=viewer,
    ).json()
    assert all(step["pieces"] == 0 and step["last_day"] == DAY for step in empty["steps"] if step["last_day"])
    assert steps["POS-CON"]["disagreements"] == 8  # machine OK at 0.35, drawing limit 0.30
    assert steps["POS-CON"]["spec_nok"] == 1 and steps["POS-CON"]["status"] == "critical"
    assert steps["LEN-CON"]["status"] in ("ok", "warning")
    assert {r["label"] for r in body["recipes"]} == {
        "Recipe 2 (variant pending)",
        "Recipe 3 (variant pending)",
    }

    recipe_3 = next(r["id"] for r in body["recipes"] if r["code"] == 3)
    filtered = client.get(
        f"/api/v1/process/lines/{line.line_id}/overview",
        params={"from": DAY, "to": DAY, "recipe_id": recipe_3},
        headers=viewer,
    ).json()
    assert {s["operation"]["code"]: s["pieces"] for s in filtered["steps"]}["TYPE"] == 1


def test_operation_summary_and_characteristic_detail(client: TestClient, viewer, line) -> None:
    operation_id = line.stations["POS-CON"].operation_id
    summary = client.get(
        f"/api/v1/process/operations/{operation_id}/summary", params={"from": DAY, "to": DAY}, headers=viewer
    ).json()
    codes = [c["code"] for c in summary["characteristics"]]
    assert codes[:3] == ["POS-CON-P1X", "POS-CON-P1Y", "POS-CON-P2X"] and len(codes) == 16
    p1x = summary["characteristics"][0]
    assert p1x["specification"]["upper_limit"] == "0.300000"
    assert p1x["capability_kind"] == "Cpu" and p1x["machine_ok_spec_nok"] == 1
    assert sum(row["pieces"] for row in summary["by_nest"]) == summary["pieces"] == 2
    assert summary["coverage"] == 1.0 and summary["partial_logging"] is False
    # The step page offers the line's recipes and filters by the chosen one.
    assert [r["code"] for r in summary["recipes"]] == [2, 3]
    recipe_3 = next(r["id"] for r in summary["recipes"] if r["code"] == 3)
    only_3 = client.get(
        f"/api/v1/process/operations/{operation_id}/summary",
        params={"from": DAY, "to": DAY, "recipe_id": recipe_3},
        headers=viewer,
    ).json()
    assert only_3["pieces"] == 1 and [row["pieces"] for row in only_3["by_recipe"]] == [1]

    detail = client.get(
        f"/api/v1/process/operations/{operation_id}/characteristics/{p1x['id']}",
        params={"from": DAY, "to": DAY, "bins": 10},
        headers=viewer,
    ).json()
    assert len(detail["bins"]) == 10
    assert sum(b["count"] for b in detail["bins"]) + detail["below_range"] + detail["above_range"] == 2
    assert detail["daily"][0]["n"] == 2


def test_piece_trace_keeps_both_verdicts(client: TestClient, viewer, line) -> None:
    trace = client.get("/api/v1/process/pieces/900002", headers=viewer).json()
    assert trace["recipe"]["label"] == "Recipe 3 (variant pending)"
    steps = {step["operation"]["code"]: step for step in trace["steps"]}
    assert set(steps) == {"ET1", "LEN-PCB", "LEN-CON", "POS-PCB", "POS-CON", "TYPE"}
    p1x = next(v for v in steps["POS-CON"]["values"] if v["code"] == "POS-CON-P1X")
    assert p1x["machine_ok"] is True and p1x["is_ok"] is False
    ref = next(v for v in steps["LEN-CON"]["values"] if v["code"] == "LEN-CON-REF")
    assert ref["specification"] is None and ref["is_ok"] is None

    assert client.get("/api/v1/process/pieces/900003", headers=viewer).status_code == 404  # out of scope
    assert client.get("/api/v1/process/pieces/not-a-serial", headers=viewer).status_code == 422


def test_position_map_pairs_x_and_y_against_the_tolerance(client: TestClient, viewer, line) -> None:
    ops = {
        op["code"]: op["id"]
        for op in client.get("/api/v1/process/lines", headers=viewer).json()[0]["operations"]
    }
    url = f"/api/v1/process/operations/{ops['POS-CON']}/position-map"
    body = client.get(url, params={"pin": 1, "from": DAY, "to": DAY}, headers=viewer).json()

    assert body["pins"] == list(range(1, 9))
    assert body["tolerance_x"] == 0.3 and body["tolerance_y"] == 0.3
    assert body["extent"] == 0.6
    # 900001 sits inside (0.08, 0.04); 900002 is outside in X only (0.35, 0.175).
    assert body["total"]["pieces"] == 2
    assert body["total"]["out_of_tolerance"] == 1
    assert (body["total"]["out_x"], body["total"]["out_y"]) == (1, 0)
    assert sum(cell["count"] for cell in body["cells"]) == 2 and body["beyond_extent"] == 0
    # Radial: 900002 at sqrt(0.35^2 + 0.175^2) = 0.39 is outside the 0.30 circle.
    assert body["total"]["out_radial"] == 1
    assert body["sampled_from"] == 2 and len(body["points"]) == 2
    assert {round(p["x"], 3) for p in body["points"]} == {0.08, 0.35}
    assert [nest["nest"] for nest in body["nests"]] == [1, 2]
    assert body["nests"][1]["out_of_tolerance"] == 1

    recipe_3 = next(
        r["id"]
        for r in client.get(
            f"/api/v1/process/lines/{line.line_id}/overview", params={"from": DAY, "to": DAY}, headers=viewer
        ).json()["recipes"]
        if r["code"] == 3
    )
    filtered = client.get(
        url, params={"pin": 1, "from": DAY, "to": DAY, "recipe_id": recipe_3}, headers=viewer
    ).json()
    assert filtered["total"]["pieces"] == 1

    no_xy = client.get(f"/api/v1/process/operations/{ops['LEN-CON']}/position-map", headers=viewer)
    assert no_xy.status_code == 404
    assert client.get(url).status_code == 401
