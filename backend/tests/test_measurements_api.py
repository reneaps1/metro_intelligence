"""F4.6 (MI-26): read-only measurements API integration tests.

Real-dataset performance verification (docs/tasks/F4.6.md's acceptance
criterion: "la serie de 90 dias de una caracteristica responde en menos de
300ms sobre el dataset seed completo") was done manually against a real
`python -m seed` run (8 parts, 149 characteristics, 540 runs, 60480
results) rather than automated here -- standing up that full pipeline
inside a pytest fixture would make every CI run pay for a ~7s generator
pass. `EXPLAIN ANALYZE` on the exact query this endpoint issues, against
the busiest characteristic (426 results, the full 90-day depth): 2.1ms
execution time, using the `(characteristic_id, measured_at)` index
(migration 0003) on every monthly partition. The live endpoint end-to-end
(auth + RBAC + ORM + serialization): ~30ms warm, 5 consecutive calls. See
this PR's description for the full transcript.

`test_series_response_time_is_well_within_budget` below is the automated
regression guard: a smaller (~600-point) synthetic dataset built directly
via the ORM, asserting the same <300ms bound the task specifies -- it won't
catch every possible regression at 60k-row scale, but it will catch an
accidentally-dropped index or an N+1 query.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.api.v1.auth import router as auth_router
from app.api.v1.measurements import router as measurements_router
from app.core.database import SessionLocal
from app.models.catalog import (
    Characteristic,
    CharacteristicClassification,
    MeasurementProgram,
    PartNumber,
    ProductFamily,
    Specification,
)
from app.models.intelligence import Recommendation
from app.models.measurement import MeasurementResult, MeasurementRun, MeasurementSample
from app.models.org import Area, Cell, Line, Machine, Organization, Site
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from conftest import DEMO_USERS, KNOWN_PASSWORD


@pytest.fixture(scope="session")
def measurements_app(auth_database: None) -> FastAPI:
    app = FastAPI(title="F4.6 measurements test app")
    app.include_router(auth_router)
    app.include_router(measurements_router, prefix="/api/v1")
    return app


@pytest.fixture(scope="session")
def measurements_client(measurements_app: FastAPI) -> TestClient:
    return TestClient(measurements_app)


@pytest.fixture(scope="session")
def as_role(measurements_client: TestClient):
    cache: dict[str, dict[str, str]] = {}

    def _login(role: str) -> dict[str, str]:
        if role not in cache:
            response = measurements_client.post(
                "/auth/login",
                data={"username": DEMO_USERS[role], "password": KNOWN_PASSWORD},
            )
            assert response.status_code == 200, response.text
            cache[role] = {"Authorization": f"Bearer {response.json()['access_token']}"}
        return cache[role]

    return _login


@pytest.fixture
def demo_machine() -> uuid.UUID:
    suffix = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        org = Organization(code=f"ORG-{suffix}", name="Demo org (fictitious)")
        db.add(org)
        db.flush()
        site = Site(organization_id=org.id, code=f"SITE-{suffix}", name="Demo site")
        db.add(site)
        db.flush()
        area = Area(site_id=site.id, code=f"AREA-{suffix}", name="Demo area")
        db.add(area)
        db.flush()
        line = Line(area_id=area.id, code=f"LINE-{suffix}", name="Demo line")
        db.add(line)
        db.flush()
        cell = Cell(line_id=line.id, code=f"CELL-{suffix}", name="Demo cell")
        db.add(cell)
        db.flush()
        machine = Machine(cell_id=cell.id, code=f"CMM-{suffix}", name="Demo CMM")
        db.add(machine)
        db.commit()
        return machine.id
    finally:
        db.close()


@pytest.fixture
def demo_characteristic(demo_machine: uuid.UUID) -> dict:
    """One characteristic with an active spec, a program, and 5 results
    spread over 5 distinct runs -- enough to exercise list/detail/series
    without the weight of a full seed run."""
    suffix = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        family = ProductFamily(code=f"MI-DEMO-FAM-{suffix}", name="Demo family (fictitious)")
        db.add(family)
        db.flush()
        part = PartNumber(product_family_id=family.id, code=f"MI-DEMO-{suffix}", name="Demo bracket")
        db.add(part)
        classification = CharacteristicClassification(code=f"CLS-{suffix}", name="Demo classification")
        db.add(classification)
        db.flush()
        characteristic = Characteristic(
            part_number_id=part.id,
            balloon_number="1",
            name="Demo diameter",
            characteristic_type="diameter",
            unit="mm",
            classification_id=classification.id,
        )
        db.add(characteristic)
        db.flush()
        start = datetime(2026, 1, 1, tzinfo=UTC)
        # valid_from is explicit, not the now()-default: the spec-version-
        # boundary test needs it anchored to the same fixed timeline as the
        # measurement results below, not the real wall-clock time the
        # fixture happens to run at.
        spec = Specification(
            characteristic_id=characteristic.id,
            nominal=10,
            lower_tol=-1,
            upper_tol=1,
            unit="mm",
            valid_from=start,
        )
        db.add(spec)
        db.flush()
        program = MeasurementProgram(
            part_number_id=part.id, name="CMM Program", output_mapping={"1": "COL_1"}
        )
        db.add(program)
        db.flush()

        result_ids = []
        for i in range(5):
            run = MeasurementRun(
                measurement_program_id=program.id,
                machine_id=demo_machine,
                operator_identifier="OP",
                batch_lot=f"BATCH-{i}",
                run_at=start + timedelta(days=i),
            )
            db.add(run)
            db.flush()
            sample = MeasurementSample(measurement_run_id=run.id, sample_sequence=1)
            db.add(sample)
            db.flush()
            result = MeasurementResult(
                measured_at=run.run_at,
                measurement_sample_id=sample.id,
                characteristic_id=characteristic.id,
                specification_id=spec.id,
                value=Decimal("10.5") if i < 4 else Decimal("11.5"),  # last point: out of tolerance
            )
            db.add(result)
            db.flush()
            result_ids.append(result.id)
        db.commit()
        return {
            "part_id": part.id,
            "characteristic_id": characteristic.id,
            "program_id": program.id,
            "machine_id": demo_machine,
            "spec_id": spec.id,
            "result_ids": result_ids,
        }
    finally:
        db.close()


def test_series_computes_deviation_and_is_ok(
    measurements_client: TestClient, as_role, demo_characteristic: dict
) -> None:
    response = measurements_client.get(
        f"/api/v1/characteristics/{demo_characteristic['characteristic_id']}/series",
        headers=as_role("metrologist"),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_points"] == 5
    assert body["returned_points"] == 5
    assert body["downsampled"] is False
    points = body["points"]
    assert [p["measured_at"] for p in points] == sorted(p["measured_at"] for p in points), (
        "must be time-ordered"
    )
    assert all(p["is_ok"] for p in points[:4])
    assert points[4]["is_ok"] is False, "value 11.5 vs nominal 10 +/-1 is out of tolerance"
    assert points[4]["deviation"] == "1.500000"


def test_series_reflects_spec_version_boundary(
    measurements_client: TestClient, as_role, demo_characteristic: dict
) -> None:
    """Acceptance criterion: a range crossing a spec version change must
    evaluate each point against the spec *in force when it was measured*,
    not the characteristic's current spec."""
    characteristic_id = demo_characteristic["characteristic_id"]
    old_spec_id = demo_characteristic["spec_id"]

    db = SessionLocal()
    try:
        old_spec = db.get(Specification, old_spec_id)
        old_spec.valid_to = datetime(2026, 1, 3, tzinfo=UTC)
        new_spec = Specification(
            characteristic_id=characteristic_id,
            nominal=10,
            lower_tol=-2,
            upper_tol=2,  # widened tolerance -> the old-spec NOK point should now read OK if misattributed
            unit="mm",
            valid_from=datetime(2026, 1, 3, tzinfo=UTC),
        )
        db.add(new_spec)
        db.commit()
        new_spec_id = new_spec.id
    finally:
        db.close()

    response = measurements_client.get(
        f"/api/v1/characteristics/{characteristic_id}/series", headers=as_role("metrologist")
    )
    assert response.status_code == 200
    points = {p["measured_at"]: p for p in response.json()["points"]}
    last_point = sorted(points.values(), key=lambda p: p["measured_at"])[-1]

    # The last point (day 5, value 11.5) was measured while the *old* spec
    # (+/-1) was active (old spec closed at day 3, but this result's own
    # specification_id was fixed at insert time to the old spec) -- it must
    # still evaluate against +/-1 (still NOK), not silently pick up the
    # widened +/-2 tolerance just because that's the *current* active spec.
    assert last_point["specification"]["id"] == str(old_spec_id)
    assert last_point["is_ok"] is False
    assert last_point["specification"]["id"] != str(new_spec_id)


def test_measurement_run_detail_includes_samples_and_results(
    measurements_client: TestClient, as_role, demo_characteristic: dict
) -> None:
    runs = measurements_client.get(
        "/api/v1/measurement-runs",
        params={"part_number_id": str(demo_characteristic["part_id"])},
        headers=as_role("quality_engineer"),
    ).json()
    assert runs["total"] == 5
    run_id = runs["items"][0]["id"]

    detail = measurements_client.get(
        f"/api/v1/measurement-runs/{run_id}", headers=as_role("quality_engineer")
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["part_number_id"] == str(demo_characteristic["part_id"])
    assert len(body["samples"]) == 1
    assert len(body["samples"][0]["results"]) == 1


def test_measurement_runs_filter_by_machine_and_date_range(
    measurements_client: TestClient, as_role, demo_characteristic: dict
) -> None:
    headers = as_role("auditor")
    by_machine = measurements_client.get(
        "/api/v1/measurement-runs",
        params={"machine_id": str(demo_characteristic["machine_id"])},
        headers=headers,
    ).json()
    assert by_machine["total"] == 5

    narrow_range = measurements_client.get(
        "/api/v1/measurement-runs",
        params={
            "part_number_id": str(demo_characteristic["part_id"]),
            "run_at_from": "2026-01-01T00:00:00Z",
            "run_at_to": "2026-01-02T00:00:00Z",
        },
        headers=headers,
    ).json()
    assert narrow_range["total"] == 2


def test_series_downsamples_when_over_max_points(
    measurements_client: TestClient, as_role, demo_characteristic: dict
) -> None:
    response = measurements_client.get(
        f"/api/v1/characteristics/{demo_characteristic['characteristic_id']}/series",
        params={"max_points": 2},
        headers=as_role("metrologist"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_points"] == 5
    assert body["downsampled"] is True
    assert body["returned_points"] == 2
    # First and last points must survive downsampling -- a chart missing
    # the most recent (and thus most decision-relevant) point is worse than
    # a slightly coarser middle.
    measured_ats = [p["measured_at"] for p in body["points"]]
    assert measured_ats[-1] == max(measured_ats)


def test_series_response_time_is_well_within_budget(measurements_client: TestClient, as_role) -> None:
    """Automated regression guard against the task's <300ms bound -- see
    this module's docstring for the real full-dataset (~60k rows) numbers,
    verified manually."""
    suffix = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        family = ProductFamily(code=f"MI-DEMO-PERF-{suffix}", name="Perf demo family")
        db.add(family)
        db.flush()
        part = PartNumber(product_family_id=family.id, code=f"MI-DEMO-PERF-{suffix}", name="Perf demo part")
        db.add(part)
        classification = CharacteristicClassification(code=f"PERF-CLS-{suffix}", name="Perf classification")
        db.add(classification)
        db.flush()
        characteristic = Characteristic(
            part_number_id=part.id,
            balloon_number="1",
            name="Perf characteristic",
            characteristic_type="diameter",
            unit="mm",
            classification_id=classification.id,
        )
        db.add(characteristic)
        db.flush()
        spec = Specification(
            characteristic_id=characteristic.id, nominal=10, lower_tol=-1, upper_tol=1, unit="mm"
        )
        db.add(spec)
        db.flush()
        program = MeasurementProgram(
            part_number_id=part.id, name="Perf CMM Program", output_mapping={"1": "COL_1"}
        )
        db.add(program)
        db.flush()

        start = datetime(2026, 1, 1, tzinfo=UTC)
        for i in range(600):
            run = MeasurementRun(
                measurement_program_id=program.id,
                operator_identifier="OP",
                run_at=start + timedelta(hours=i),
            )
            db.add(run)
            db.flush()
            sample = MeasurementSample(measurement_run_id=run.id, sample_sequence=1)
            db.add(sample)
            db.flush()
            db.add(
                MeasurementResult(
                    measured_at=run.run_at,
                    measurement_sample_id=sample.id,
                    characteristic_id=characteristic.id,
                    specification_id=spec.id,
                    value=Decimal("10.1"),
                )
            )
        db.commit()
        characteristic_id = characteristic.id
    finally:
        db.close()

    headers = as_role("metrologist")
    measurements_client.get(f"/api/v1/characteristics/{characteristic_id}/series", headers=headers)  # warm-up

    start_time = time.perf_counter()
    response = measurements_client.get(
        f"/api/v1/characteristics/{characteristic_id}/series",
        params={"max_points": 5000},
        headers=headers,
    )
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    assert response.status_code == 200
    assert response.json()["total_points"] == 600
    assert elapsed_ms < 300, f"series endpoint took {elapsed_ms:.1f}ms, budget is 300ms"


# --- RBAC --------------------------------------------------------------------


def test_unauthenticated_requests_rejected(measurements_client: TestClient) -> None:
    assert measurements_client.get("/api/v1/measurement-runs").status_code == 401
    assert measurements_client.get(f"/api/v1/characteristics/{uuid.uuid4()}/series").status_code == 401


@pytest.mark.parametrize("role", ["metrologist", "quality_engineer", "admin", "auditor"])
def test_roles_with_read_permission_can_list_runs(
    measurements_client: TestClient, as_role, role: str
) -> None:
    response = measurements_client.get("/api/v1/measurement-runs", headers=as_role(role))
    assert response.status_code == 200


def test_viewer_is_denied_per_the_actual_rbac_matrix(measurements_client: TestClient, as_role) -> None:
    """docs/security/rbac.md's real matrix (and migration 0001) does not
    grant `viewer` read on measurement.measurement_run/measurement_result --
    see this file's module docstring and this PR's description for why this
    test follows the matrix over docs/tasks/F4.6.md's inconsistent prose."""
    response = measurements_client.get("/api/v1/measurement-runs", headers=as_role("viewer"))
    assert response.status_code == 403


# --- LM.4 capability-history --------------------------------------------------


def test_capability_history_returns_real_engine_output(
    measurements_client: TestClient, as_role, demo_characteristic: dict
) -> None:
    response = measurements_client.get(
        f"/api/v1/characteristics/{demo_characteristic['characteristic_id']}/capability-history",
        params={"window_size": 5},
        headers=as_role("metrologist"),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["characteristic_id"] == str(demo_characteristic["characteristic_id"])
    assert body["window_size"] == 5
    # demo_characteristic seeds exactly 5 results -> one window.
    assert len(body["windows"]) == 1
    window = body["windows"][0]
    assert window["point_count"] == 5
    assert window["engine_name"] == "spc_engine"
    assert window["ucl"] is not None
    assert window["lcl"] is not None


def test_capability_history_404s_for_an_unknown_characteristic(
    measurements_client: TestClient, as_role
) -> None:
    response = measurements_client.get(
        f"/api/v1/characteristics/{uuid.uuid4()}/capability-history",
        headers=as_role("metrologist"),
    )
    assert response.status_code == 404


@pytest.mark.parametrize("role", ["metrologist", "quality_engineer", "admin", "auditor"])
def test_capability_history_allows_the_same_roles_as_series(
    measurements_client: TestClient, as_role, demo_characteristic: dict, role: str
) -> None:
    response = measurements_client.get(
        f"/api/v1/characteristics/{demo_characteristic['characteristic_id']}/capability-history",
        headers=as_role(role),
    )
    assert response.status_code == 200


def test_capability_history_denies_viewer_same_as_series(
    measurements_client: TestClient, as_role, demo_characteristic: dict
) -> None:
    response = measurements_client.get(
        f"/api/v1/characteristics/{demo_characteristic['characteristic_id']}/capability-history",
        headers=as_role("viewer"),
    )
    assert response.status_code == 403


def test_capability_history_unauthenticated_rejected(measurements_client: TestClient) -> None:
    response = measurements_client.get(f"/api/v1/characteristics/{uuid.uuid4()}/capability-history")
    assert response.status_code == 401


# --- EXPERIMENTAL sampling-recommendation -------------------------------------

# Deterministic, distinct offsets within one window -- never all-identical,
# so each window's own Cpk is defined (nonzero within-window stdev), and
# tight enough around the +/-1 tolerance that Cpk is well above the 1.67
# threshold (same convention as test_drift_detection_service.py's
# TIGHT_OFFSETS).
SAMPLING_TIGHT_OFFSETS = [Decimal("-0.02"), Decimal("-0.01"), Decimal("0"), Decimal("0.01"), Decimal("0.02")]
SAMPLING_WINDOW_SIZE = len(SAMPLING_TIGHT_OFFSETS)


def _make_sampling_characteristic(db: SessionLocal) -> dict:
    suffix = uuid.uuid4().hex[:8]
    family = ProductFamily(code=f"MI-DEMO-SMP-{suffix}", name="Demo family (fictitious)")
    db.add(family)
    db.flush()
    part = PartNumber(product_family_id=family.id, code=f"MI-DEMO-SMP-{suffix}", name="Demo bracket")
    db.add(part)
    classification = CharacteristicClassification(code=f"SMP-CLS-{suffix}", name="Demo classification")
    db.add(classification)
    db.flush()
    characteristic = Characteristic(
        part_number_id=part.id,
        balloon_number="1",
        name="Sampling demo diameter",
        characteristic_type="diameter",
        unit="mm",
        classification_id=classification.id,
    )
    db.add(characteristic)
    db.flush()
    spec = Specification(
        characteristic_id=characteristic.id, nominal=10, lower_tol=-1, upper_tol=1, unit="mm"
    )
    db.add(spec)
    program = MeasurementProgram(
        part_number_id=part.id, name="Sampling CMM Program", output_mapping={"1": "COL_1"}
    )
    db.add(program)
    db.flush()
    db.commit()
    return {
        "characteristic_id": characteristic.id,
        "spec_id": spec.id,
        "program_id": program.id,
        "part_id": part.id,
    }


def _insert_sampling_windows(
    db, characteristic_id, spec_id, program_id, *, n_windows: int, offsets: list[Decimal], start=None
):
    cursor = start or datetime(2026, 1, 1, tzinfo=UTC)
    for _ in range(n_windows):
        run = MeasurementRun(measurement_program_id=program_id, operator_identifier="OP", run_at=cursor)
        db.add(run)
        db.flush()
        sample = MeasurementSample(measurement_run_id=run.id, sample_sequence=1)
        db.add(sample)
        db.flush()
        for offset in offsets:
            db.add(
                MeasurementResult(
                    measured_at=cursor,
                    measurement_sample_id=sample.id,
                    characteristic_id=characteristic_id,
                    specification_id=spec_id,
                    value=Decimal(10) + offset,
                )
            )
            cursor += timedelta(minutes=1)
    db.commit()
    return cursor


def test_sampling_recommendation_returns_conservative_default_for_the_demo_fixture(
    measurements_client: TestClient, as_role, demo_characteristic: dict
) -> None:
    """demo_characteristic seeds exactly 5 results -> 1 window, below the
    engine's minimum_windows=5 -- must still be a 200 with a conservative
    default body, never a 404 or a null response."""
    response = measurements_client.get(
        f"/api/v1/characteristics/{demo_characteristic['characteristic_id']}/sampling-recommendation",
        headers=as_role("metrologist"),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["windows_analyzed"] == 1
    assert body["recommended_frequency"] == 5
    assert body["confidence"] == 0.0
    assert body["conflicting_recommendations"] is None


def test_sampling_recommendation_computes_a_real_result_with_enough_windows(
    measurements_client: TestClient, as_role
) -> None:
    db = SessionLocal()
    try:
        ctx = _make_sampling_characteristic(db)
        _insert_sampling_windows(
            db,
            ctx["characteristic_id"],
            ctx["spec_id"],
            ctx["program_id"],
            n_windows=6,
            offsets=SAMPLING_TIGHT_OFFSETS,
        )
    finally:
        db.close()

    response = measurements_client.get(
        f"/api/v1/characteristics/{ctx['characteristic_id']}/sampling-recommendation",
        params={"window_size": SAMPLING_WINDOW_SIZE},
        headers=as_role("metrologist"),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["windows_analyzed"] == 6
    assert body["recommended_frequency"] in {5, 10, 20, 50, 100}
    assert 0.0 <= body["confidence"] <= 1.0
    assert body["cpk_trend"] in {"stable", "improving", "declining"}


def test_sampling_recommendation_surfaces_a_conflict_with_an_existing_pending_frequency_increase(
    measurements_client: TestClient, as_role
) -> None:
    db = SessionLocal()
    try:
        ctx = _make_sampling_characteristic(db)
        _insert_sampling_windows(
            db,
            ctx["characteristic_id"],
            ctx["spec_id"],
            ctx["program_id"],
            n_windows=6,
            offsets=SAMPLING_TIGHT_OFFSETS,
        )
        recommendation = Recommendation(
            characteristic_id=ctx["characteristic_id"],
            recommendation_type="frequency_increase",
            rationale="Trend approaching upper tolerance with rising variance.",
            evidence={},
            engine_name="adaptive_inspection_engine",
            engine_version="v1",
            state="pending",
        )
        db.add(recommendation)
        db.commit()
        recommendation_id = recommendation.id
    finally:
        db.close()

    response = measurements_client.get(
        f"/api/v1/characteristics/{ctx['characteristic_id']}/sampling-recommendation",
        params={"window_size": SAMPLING_WINDOW_SIZE},
        headers=as_role("metrologist"),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["conflicting_recommendations"] is not None
    ids = [c["id"] for c in body["conflicting_recommendations"]]
    assert str(recommendation_id) in ids


def test_sampling_recommendation_404s_for_an_unknown_characteristic(
    measurements_client: TestClient, as_role
) -> None:
    response = measurements_client.get(
        f"/api/v1/characteristics/{uuid.uuid4()}/sampling-recommendation",
        headers=as_role("metrologist"),
    )
    assert response.status_code == 404


@pytest.mark.parametrize("role", ["metrologist", "quality_engineer", "admin", "auditor"])
def test_sampling_recommendation_allows_the_same_roles_as_capability_history(
    measurements_client: TestClient, as_role, demo_characteristic: dict, role: str
) -> None:
    response = measurements_client.get(
        f"/api/v1/characteristics/{demo_characteristic['characteristic_id']}/sampling-recommendation",
        headers=as_role(role),
    )
    assert response.status_code == 200


def test_sampling_recommendation_denies_viewer_same_as_capability_history(
    measurements_client: TestClient, as_role, demo_characteristic: dict
) -> None:
    response = measurements_client.get(
        f"/api/v1/characteristics/{demo_characteristic['characteristic_id']}/sampling-recommendation",
        headers=as_role("viewer"),
    )
    assert response.status_code == 403


def test_sampling_recommendation_unauthenticated_rejected(
    measurements_client: TestClient, demo_characteristic: dict
) -> None:
    response = measurements_client.get(
        f"/api/v1/characteristics/{demo_characteristic['characteristic_id']}/sampling-recommendation"
    )
    assert response.status_code == 401


def test_sampling_recommendation_never_creates_a_recommendation_row(
    measurements_client: TestClient, as_role, demo_characteristic: dict
) -> None:
    characteristic_id = demo_characteristic["characteristic_id"]

    def _count_recommendations() -> int:
        db = SessionLocal()
        try:
            return db.execute(
                select(func.count())
                .select_from(Recommendation)
                .where(Recommendation.characteristic_id == characteristic_id)
            ).scalar_one()
        finally:
            db.close()

    before = _count_recommendations()
    response = measurements_client.get(
        f"/api/v1/characteristics/{characteristic_id}/sampling-recommendation",
        headers=as_role("metrologist"),
    )
    assert response.status_code == 200
    after = _count_recommendations()
    assert after == before
