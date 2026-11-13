"""Line ingestion end to end on synthetic station files (ADR-004/005)."""

from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

alembic_command = pytest.importorskip("alembic.command")
alembic_config = pytest.importorskip("alembic.config")
sa = pytest.importorskip("sqlalchemy")

from app.engines.spc.capability import (  # noqa: E402
    Moments,
    ToleranceSpec,
    cp,
    cp_from_moments,
    cpk,
    cpk_from_moments,
)
from app.ingest import loader as loader_module  # noqa: E402
from app.ingest.loader import LineLoader  # noqa: E402
from app.ingest.setup import ensure_catalog  # noqa: E402
from app.ingest.specs import import_specifications, parse_spec_file  # noqa: E402
from app.ingest.stats import build_daily_stats  # noqa: E402
from app.services.domain_purge import truncate_domain_tables  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from line_csv_factory import LineFiles, Piece, length_row, make_config, raw_row  # noqa: E402

TEST_DATABASE_URL = os.getenv("METRO_TEST_DATABASE_URL")
BACKEND_DIR = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="Set METRO_TEST_DATABASE_URL to a disposable PostgreSQL database."
)
DAY = "2026-03-02"
SPECS = {
    "source": "MI-DEMO drawing rev A",
    "valid_from": "2025-01-01T00:00:00Z",
    "specifications": [
        {"station": "LEN-CON", "measure": "pin", "nominal": 5.5, "lower_tol": -0.3, "upper_tol": 0.3},
        {"station": "LEN-PCB", "measure": "pin", "nominal": 10.0, "upper_tol": 0.0},
        {"station": "POS-PCB", "measure": "pin", "nominal": 0.0, "upper_tol": 0.35},
        {"station": "POS-CON", "measure": "pin_x", "nominal": 0.0, "upper_tol": 0.30},
        {"station": "POS-CON", "measure": "pin_y", "nominal": 0.0, "upper_tol": 0.30},
    ],
}


@pytest.fixture(scope="module")
def engine():
    cfg = alembic_config.Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    alembic_command.upgrade(cfg, "head")
    eng = sa.create_engine(TEST_DATABASE_URL)
    yield eng
    eng.dispose()
    alembic_command.downgrade(cfg, "base")


@pytest.fixture(autouse=True)
def clean(engine):
    with engine.begin() as conn:
        truncate_domain_tables(conn)
    yield


def _setup(engine, *, with_specs: bool = True):
    config = make_config()
    with Session(engine) as session:
        catalog = ensure_catalog(session, config, datetime(2026, 1, 1, tzinfo=config.timezone))
        if with_specs:
            import_specifications(session, config, catalog, parse_spec_file(SPECS))
        session.commit()
    return config, catalog


def _load(engine, config, catalog, data_dir: Path, **kwargs):
    loader = LineLoader(engine, config, catalog, data_dir, storage=None, raw_bucket="")
    loader.scan_recipes()
    loader.load_state()
    return loader.load(**kwargs)


def _scalar(engine, sql: str, **params):
    with engine.connect() as conn:
        return conn.execute(sa.text(sql), params).scalar_one()


def _pieces() -> list[Piece]:
    return [
        Piece("100001", recipe=2, nest=1, second=10),
        Piece(
            "100002", recipe=3, nest=2, second=20, pos_con=0.35
        ),  # machine OK (<=0.40), drawing NOK (>0.30)
        Piece("100003", recipe=1, nest=3, second=30),  # other product: out of scope everywhere
        Piece(
            "100004", recipe=2, nest=1, second=40, length_con=5.95
        ),  # connector length out of drawing tolerance
    ]


def test_scope_attempts_quarantine_and_values(engine, tmp_path):
    config, catalog = _setup(engine)
    files = LineFiles(day=DAY, pieces=_pieces())
    files.extra_rows = {
        # a piece scrapped before type check, seen at a program-2 station
        "05_pos_pcb": [
            raw_row(
                f"{DAY.replace('-', '')}-01:00:00",
                "100099",
                "4",
                "2",
                "True",
                *(["True", "0.100"] * 8),
                "False",
                "0",
            )
        ],
        # unreadable piece id on an in-scope program -> quarantined
        "06_pos_con": [
            raw_row(
                f"{DAY.replace('-', '')}-01:00:01",
                "0",
                "4",
                "2",
                "True",
                *(["True", "0.1", "True", "0.1"] * 9),
            )
        ],
        # a length row for a piece never seen at type check -> scope unknown; a repeat of 100001 -> attempt 2
        "04_len_con": [length_row(DAY, "777777", 5.5), length_row(DAY, "100001", 5.46)],
    }
    files.write(tmp_path)

    summary = _load(engine, config, catalog, tmp_path)
    totals = summary.totals_by_station()

    assert totals["TYPE"]["rows_loaded"] == 3 and totals["TYPE"]["excluded_recipe"] == 1
    assert totals["POS-PCB"]["excluded_program"] == 1 and totals["POS-PCB"]["pieces_without_recipe"] == 1
    assert totals["POS-CON"]["quarantined"] == 1
    assert totals["LEN-CON"]["scope_unknown"] == 1 and totals["LEN-CON"]["repeat_attempts"] == 1
    assert totals["LEN-CON"]["excluded_recipe"] == 1
    for station, counter in totals.items():
        accounted = sum(
            counter[k]
            for k in ("rows_loaded", "excluded_recipe", "excluded_program", "scope_unknown", "quarantined")
        )
        assert counter["rows_read"] == accounted, station

    assert _scalar(engine, "SELECT count(*) FROM process_part_instances") == 4  # 3 typed + 1 orphan
    assert _scalar(engine, "SELECT count(*) FROM process_part_instances WHERE serial_number = '100003'") == 0
    assert _scalar(engine, "SELECT count(*) FROM process_part_instances WHERE recipe_id IS NULL") == 1
    assert _scalar(engine, "SELECT max(attempt_no) FROM process_step_results") == 2

    # position 9 is filler for an 8-pin product: never loaded
    assert (
        _scalar(engine, "SELECT count(*) FROM catalog_characteristics WHERE balloon_number LIKE '%P9%'") == 0
    )
    # length: reference + 8 pins per piece row
    assert (
        _scalar(
            engine,
            "SELECT count(*) FROM measurement_results r JOIN catalog_characteristics c ON c.id = r.characteristic_id "
            "WHERE c.balloon_number LIKE 'LEN-CON-%'",
        )
        == 9 * 4
    )  # 3 typed pieces + 1 repeat
    # the electrical sentinel value 2 is dropped; value 1 keeps 9 decimals
    assert (
        _scalar(
            engine,
            "SELECT count(*) FROM catalog_characteristics WHERE balloon_number LIKE 'ET1-%V2'",
        )
        == 0
    )
    assert _scalar(
        engine,
        "SELECT min(value) FROM measurement_results r JOIN catalog_characteristics c "
        "ON c.id = r.characteristic_id WHERE c.balloon_number LIKE 'ET1-%'",
    ) == Decimal("0.805512100")

    # machine verdict and drawing verdict are kept apart
    assert (
        _scalar(
            engine,
            "SELECT count(*) FROM measurement_results r JOIN catalog_characteristics c ON c.id = r.characteristic_id "
            "WHERE c.balloon_number LIKE 'POS-CON-P%X' AND r.machine_ok AND r.is_ok = false",
        )
        == 8
    )
    # reference values have no specification
    assert (
        _scalar(
            engine,
            "SELECT count(*) FROM measurement_results r JOIN catalog_characteristics c ON c.id = r.characteristic_id "
            "WHERE c.balloon_number LIKE '%-REF' AND (r.specification_id IS NOT NULL OR r.is_ok IS NOT NULL)",
        )
        == 0
    )


def test_rerun_is_idempotent(engine, tmp_path):
    config, catalog = _setup(engine)
    LineFiles(day=DAY, pieces=_pieces()).write(tmp_path)
    _load(engine, config, catalog, tmp_path)
    before = _scalar(engine, "SELECT count(*) FROM measurement_results")

    summary = _load(engine, config, catalog, tmp_path)
    assert all(outcome.skipped_already_loaded for outcome in summary.files)
    assert _scalar(engine, "SELECT count(*) FROM measurement_results") == before


def test_failure_mid_file_leaves_nothing(engine, tmp_path, monkeypatch):
    config, catalog = _setup(engine)
    LineFiles(day=DAY, pieces=_pieces()).write(tmp_path)
    original = loader_module._copy

    def failing_copy(conn, target, rows):
        if target.startswith("measurement_results") and rows:
            raise RuntimeError("simulated failure")
        original(conn, target, rows)

    monkeypatch.setattr(loader_module, "_copy", failing_copy)
    with pytest.raises(RuntimeError):
        _load(engine, config, catalog, tmp_path, station_codes=["TYPE", "LEN-CON"])
    # the type-check file committed; the failed length file left no rows behind
    assert _scalar(engine, "SELECT count(*) FROM measurement_imported_files") == 1
    assert (
        _scalar(
            engine,
            "SELECT count(*) FROM process_step_results sr JOIN process_operations o ON o.id = sr.operation_id "
            "WHERE o.code = 'LEN-CON'",
        )
        == 0
    )

    monkeypatch.setattr(loader_module, "_copy", original)
    _load(engine, config, catalog, tmp_path, station_codes=["TYPE", "LEN-CON"])
    assert _scalar(engine, "SELECT count(*) FROM measurement_imported_files") == 2


def test_chunked_copy_loads_the_same_rows_and_rolls_back_whole_files(engine, tmp_path, monkeypatch):
    config, catalog = _setup(engine)
    LineFiles(day=DAY, pieces=_pieces()).write(tmp_path)
    monkeypatch.setattr(loader_module, "COPY_CHUNK_ROWS", 1)
    original = loader_module._copy
    flushes = {"results": 0}

    def fail_on_second_results_flush(conn, target, rows):
        if target.startswith("measurement_results") and rows:
            flushes["results"] += 1
            if flushes["results"] == 2:
                raise RuntimeError("simulated failure")
        original(conn, target, rows)

    monkeypatch.setattr(loader_module, "_copy", fail_on_second_results_flush)
    with pytest.raises(RuntimeError):
        _load(engine, config, catalog, tmp_path, station_codes=["TYPE", "LEN-CON"])
    # the first chunk of the length file was written, then rolled back with the file
    assert _scalar(engine, "SELECT count(*) FROM measurement_results") == 0

    monkeypatch.setattr(loader_module, "_copy", original)
    _load(engine, config, catalog, tmp_path)
    chunked = _scalar(engine, "SELECT count(*) FROM measurement_results")
    pieces = _scalar(engine, "SELECT count(*) FROM process_part_instances")

    monkeypatch.setattr(loader_module, "COPY_CHUNK_ROWS", 2000)
    with engine.begin() as conn:
        truncate_domain_tables(conn)
    config, catalog = _setup(engine)
    _load(engine, config, catalog, tmp_path)
    assert _scalar(engine, "SELECT count(*) FROM measurement_results") == chunked
    assert _scalar(engine, "SELECT count(*) FROM process_part_instances") == pieces


def test_daily_stats_match_raw_results_and_follow_spec_versions(engine, tmp_path):
    config, catalog = _setup(engine)
    LineFiles(day=DAY, pieces=_pieces()).write(tmp_path)
    _load(engine, config, catalog, tmp_path)
    build_daily_stats(engine, catalog.line_id, config.timezone.key)

    with engine.connect() as conn:
        daily = conn.execute(
            sa.text(
                "SELECT c.balloon_number, sum(d.n), sum(d.n_spec_nok), sum(d.n_machine_ok_spec_nok), sum(d.sum_value) "
                "FROM process_characteristic_daily d JOIN catalog_characteristics c ON c.id = d.characteristic_id "
                "GROUP BY 1 ORDER BY 1"
            )
        ).all()
        raw = conn.execute(
            sa.text(
                "SELECT c.balloon_number, count(*), count(*) FILTER (WHERE r.is_ok = false), "
                "count(*) FILTER (WHERE r.machine_ok AND r.is_ok = false), sum(r.value::float8) "
                "FROM measurement_results r JOIN catalog_characteristics c ON c.id = r.characteristic_id "
                "GROUP BY 1 ORDER BY 1"
            )
        ).all()
    assert [row[:4] for row in daily] == [row[:4] for row in raw]
    assert all(abs(d[4] - r[4]) < 1e-9 for d, r in zip(daily, raw, strict=True))
    pieces_len_con = _scalar(
        engine,
        "SELECT sum(pieces) FROM process_step_daily d JOIN process_operations o ON o.id = d.operation_id "
        "WHERE o.code = 'LEN-CON'",
    )
    assert pieces_len_con == 3
    spec_nok_len_con = _scalar(
        engine,
        "SELECT sum(pieces_spec_nok) FROM process_step_daily d JOIN process_operations o ON o.id = d.operation_id "
        "WHERE o.code = 'LEN-CON'",
    )
    assert spec_nok_len_con == 1  # piece 100004

    # A later, wider connector-length tolerance: stats follow it, results stay untouched.
    widened = {
        **SPECS,
        "valid_from": "2026-01-01T00:00:00Z",
        "specifications": [
            {"station": "LEN-CON", "measure": "pin", "nominal": 5.5, "lower_tol": -0.3, "upper_tol": 0.6}
        ],
    }
    with Session(engine) as session:
        assert len(import_specifications(session, config, catalog, parse_spec_file(widened))) == 8
        session.commit()
    build_daily_stats(engine, catalog.line_id, config.timezone.key)
    assert (
        _scalar(
            engine,
            "SELECT sum(pieces_spec_nok) FROM process_step_daily d JOIN process_operations o ON o.id = d.operation_id "
            "WHERE o.code = 'LEN-CON'",
        )
        == 0
    )
    assert (
        _scalar(
            engine,
            "SELECT count(*) FROM measurement_results WHERE is_ok = false "
            "AND characteristic_id IN (SELECT id FROM catalog_characteristics "
            "WHERE balloon_number LIKE 'LEN-CON-P%')",
        )
        == 8
    )  # ingest-time evidence kept
    assert _scalar(engine, "SELECT count(*) FROM catalog_specifications WHERE valid_to IS NOT NULL") == 8


def test_gross_readings_stay_out_of_the_moments_but_count_as_nok(engine, tmp_path):
    config, catalog = _setup(engine)
    # 100002 reads 0.35 (out of the 0.30 drawing limit, plausible). 100005 reads
    # 8.0 in X and 4.0 in Y: both beyond 0.30 + 10 x 0.30 = 3.3, a lost pin.
    pieces = [*_pieces(), Piece("100005", recipe=2, nest=4, second=50, pos_con=8.0)]
    LineFiles(day=DAY, pieces=pieces).write(tmp_path)
    _load(engine, config, catalog, tmp_path)
    build_daily_stats(engine, catalog.line_id, config.timezone.key)

    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                "SELECT sum(d.n), sum(d.n_gross), sum(d.n_spec_nok), sum(d.sum_value), max(d.max_value) "
                "FROM process_characteristic_daily d JOIN catalog_characteristics c ON c.id = d.characteristic_id "
                "WHERE c.balloon_number = 'POS-CON-P1X'"
            )
        ).one()
    n, gross, spec_nok, total, maximum = row
    # 100001 and 100004 ok, 100002 NOK, 100005 NOK and gross (100003 is out of scope)
    assert (n, gross, spec_nok) == (4, 1, 2)
    assert total == pytest.approx(0.08 + 0.35 + 0.08)  # the gross 8.0 is not in the sum
    assert maximum == pytest.approx(8.0)  # but stays visible as the maximum

    # Lengths in tolerance and values without a specification are never gross.
    assert (
        _scalar(
            engine,
            "SELECT COALESCE(sum(d.n_gross), 0) FROM process_characteristic_daily d "
            "JOIN process_operations o ON o.id = d.operation_id WHERE o.code <> 'POS-CON'",
        )
        == 0
    )


def test_specification_import_is_idempotent(engine):
    config, catalog = _setup(engine, with_specs=False)
    with Session(engine) as session:
        first = import_specifications(session, config, catalog, parse_spec_file(SPECS))
        second = import_specifications(session, config, catalog, parse_spec_file(SPECS))
        session.commit()
    assert len(first) == 8 + 8 + 8 + 8 + 8 and second == []


def test_capability_from_moments_matches_list_based():
    values = [Decimal(v) for v in ("5.41", "5.45", "5.47", "5.44", "5.50", "5.43", "5.46")]
    spec = ToleranceSpec(nominal=Decimal("5.5"), lower_tol=Decimal("-0.3"), upper_tol=Decimal("0.3"))
    moments = Moments.of(values)
    assert abs(cp_from_moments(moments, spec) - cp(values, spec)) < Decimal("1e-20")
    assert abs(cpk_from_moments(moments, spec) - cpk(values, spec)) < Decimal("1e-20")
    upper_only = ToleranceSpec(nominal=Decimal("0"), lower_tol=None, upper_tol=Decimal("0.35"))
    assert abs(cpk_from_moments(moments, upper_only) - cpk(values, upper_only)) < Decimal("1e-20")
    with pytest.raises(ValueError):
        cp_from_moments(moments, upper_only)


def test_recipe_index_numeric_and_text_ids():
    from app.ingest.loader import RecipeIndex

    index = RecipeIndex()
    index.set("2182702", 3)
    index.set("2182703", None)
    index.set("A-77", 2)
    index.set("0042", 5)  # leading zero: kept as text, not as id 42
    assert index.lookup("2182702") == (True, 3)
    assert index.lookup("2182703") == (True, None)
    assert index.lookup("A-77") == (True, 2)
    assert index.lookup("0042") == (True, 5)
    assert index.lookup("42") == (False, None)
    assert index.lookup("99999999") == (False, None)
    assert index.count == 4
