"""IQ-F10: offline long-signal converter + per-piece reader (fictitious data only)."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest
from app.connectors.long_signal_batch import (
    FLAG_GROUPING_OUT_OF_RANGE,
    FLAG_REPEATED_SIGNATURE,
    FLAG_SENTINEL,
    Mapping,
    convert,
    inventory,
    main,
    parse_timestamp,
)
from app.connectors.pieces_file import read_pieces
from app.engines.quality_analytics.analytics import QualityFilter, overview, variable_detail

PREFIX = "PLC.Demo.Part."
HEADER = "id,address,timestamp,value\n"


def _ts(minute: int, second: int = 0) -> str:
    return f"Mon Jan 05 2026 08:{minute:02d}:{second:02d} GMT-0500 (Demo Standard Time)"


def _piece(
    pid: str, minute: int, nest: int, cav: int, a_ok: str, b_ok: str, xs: tuple[float, float, float]
) -> list[str]:
    total = "true" if a_ok == "true" and b_ok == "true" else "false"
    rows = [
        f"{pid},{PREFIX}Fixture.nNest,{_ts(minute)},{nest}",
        f"{pid},{PREFIX}Mold.nCavity,{_ts(minute)},{cav}",
        f"{pid},{PREFIX}StationA.bOk,{_ts(minute, 5)},{a_ok}",
        f"{pid},{PREFIX}StationB.bOk,{_ts(minute, 9)},{b_ok}",
        f"{pid},{PREFIX}Total.bOk,{_ts(minute, 10)},{total}",
        f"{pid},{PREFIX}Header.sCustomerCode,{_ts(minute)},SECRET-123",
    ]
    rows += [f"{pid},{PREFIX}StationA.rValue.[{i}],{_ts(minute, 5)},{x}" for i, x in enumerate(xs)]
    return rows


def _mapping(**overrides: object) -> Mapping:
    data: dict[str, object] = {
        "format": "long-signals-v1",
        "address_prefix": PREFIX,
        "id_kinds": [
            {"kind": "coded", "pattern": r"^C\d{3}$"},
            {"kind": "provisional", "pattern": r"^P\d{3}$"},
        ],
        "nest": {"address": "Fixture.nNest", "valid": [1, 4]},
        "mold_cavity": {"address": "Mold.nCavity", "valid": [1, 8]},
        "total_verdict": {"address": "Total.bOk"},
        "stations": [
            {"key": "st_a", "name": "Estación A", "address": "StationA.bOk"},
            {"key": "st_b", "name": "Estación B", "address": "StationB.bOk"},
        ],
        "variables": [
            {"key": f"x{i}", "name": f"Valor {i}", "station": "st_a", "address": f"StationA.rValue.[{i}]"}
            for i in range(3)
        ],
        "empty_cycle": {"station": "st_b"},
        "repeated_signature": {"min_repeats": 3},
        "presets": [{"key": "b_by_nest", "label": "Estación B por nido", "stations": ["st_b"]}],
    }
    data.update(overrides)
    return Mapping.model_validate(data)


@pytest.fixture
def export(tmp_path: Path) -> list[Path]:
    day1 = [
        *_piece("C001", 1, 1, 1, "true", "true", (1.0, 2.0, 3.0)),
        *_piece("C002", 2, 2, 3, "false", "true", (1.5, 2.5, 3.5)),
        *_piece("P003", 3, 3, 3, "true", "false", (1.1, 2.1, 3.1)),
        # Sentinel value and an out-of-range nest.
        *_piece("C004", 4, 9, 2, "true", "true", (40000.0, 2.2, 3.2)),
        # Empty cycle: station B failed and every value is 0 -> excluded.
        *_piece("C005", 5, 1, 1, "true", "false", (0.0, 0.0, 0.0)),
        # Frozen signature repeated 3 times.
        *_piece("C006", 6, 1, 2, "true", "true", (7.0, 7.0, 7.0)),
        *_piece("C007", 7, 2, 2, "true", "true", (7.0, 7.0, 7.0)),
        "C001,PLC.Demo.Part.Extra.bad,row,with,too,many",
        ",PLC.Demo.Part.Fixture.nNest," + _ts(1) + ",1",
        "C001,PLC.Demo.Part.Fixture.nNest,not a date,1",
    ]
    day2 = [
        *_piece("C008", 8, 3, 2, "true", "true", (7.0, 7.0, 7.0)),
        # A later value for the same piece wins (re-inspection); piece ts stays the first one.
        f"C002,{PREFIX}StationA.bOk,{_ts(30)},true",
        f"C002,{PREFIX}Total.bOk,{_ts(30)},true",
    ]
    f1, f2 = tmp_path / "day1.csv", tmp_path / "day2.csv"
    f1.write_text("﻿" + HEADER + "\n".join(day1) + "\n", encoding="utf-8")
    f2.write_text(HEADER + "\n".join(day2) + "\n", encoding="utf-8")
    return [f1, f2]


def test_parse_timestamp_uses_the_explicit_offset() -> None:
    ms, offset = parse_timestamp(_ts(1, 19), "js_date_string")  # type: ignore[misc]
    assert offset == -300
    assert ms == 1767618079000  # 2026-01-05 13:01:19 UTC
    assert parse_timestamp("garbage", "js_date_string") is None
    assert parse_timestamp("2026-01-05T08:00:00-05:00", "iso8601") == (1767618000000, -300)


def test_convert_report_and_rules(export: list[Path], tmp_path: Path) -> None:
    out = tmp_path / "dataset"
    manifest = convert(export, _mapping(), out, partitions=4)
    report = manifest["report"]
    assert report["malformed"] == {"field_count": 1, "empty_id": 1, "bad_timestamp": 1}  # type: ignore[index]
    assert report["ids_total"] == 8  # type: ignore[index]
    assert report["id_kinds"] == {"coded": 7, "provisional": 1}  # type: ignore[index]
    assert report["empty_cycles_excluded"] == 1  # type: ignore[index]
    assert report["sentinels"] == {"x0": 1}  # type: ignore[index]
    assert report["grouping_out_of_range"] == {"nest": 1}  # type: ignore[index]
    assert report["repeated_signature_pieces"] == {"st_a": 3}  # type: ignore[index]
    assert report["unmapped_by_segment"] == {"Header": 8}  # type: ignore[index]
    assert manifest["pieces"] == 7
    assert manifest["utc_offset_minutes"] == -300

    raw = gzip.decompress((out / "pieces.csv.gz").read_bytes()).decode()
    assert "SECRET" not in raw and "C00" not in raw and "PLC.Demo" not in raw  # no ids, no addresses
    rows = [line.split(",") for line in raw.strip().splitlines()]
    header, body = rows[0], rows[1:]
    assert header[:5] == ["ts_ms", "id_kind", "nest", "mold_cavity", "total_nok"]
    ts = [int(r[0]) for r in body]
    assert ts == sorted(ts)
    c002 = body[1]
    assert c002[header.index("total_nok")] == "0" and c002[header.index("st_st_a")] == "0"  # last value won
    assert int(c002[0]) == 1767618120000  # first-seen time kept
    c004 = body[3]
    assert c004[header.index("nest")] == "" and c004[header.index("v_x0")] == ""
    assert int(c004[header.index("flags")]) == FLAG_SENTINEL | FLAG_GROUPING_OUT_OF_RANGE
    assert all(int(r[header.index("flags")]) & FLAG_REPEATED_SIGNATURE for r in body[4:])


def test_output_is_identical_for_any_partition_count(export: list[Path], tmp_path: Path) -> None:
    a = convert(export, _mapping(), tmp_path / "a", partitions=1)
    b = convert(export, _mapping(), tmp_path / "b", partitions=5)
    assert a["pieces_sha256"] == b["pieces_sha256"]


def test_refuses_output_inside_a_repository(export: list[Path], tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    with pytest.raises(ValueError, match="inside a repository"):
        convert(export, _mapping(), repo / "data", partitions=1)
    convert(export, _mapping(), repo / "demo-private" / "data", partitions=1)


def test_mapping_rejects_inconsistencies() -> None:
    with pytest.raises(ValueError):
        _mapping(empty_cycle={"station": "nope"})
    with pytest.raises(ValueError):
        _mapping(variables=[{"key": "x", "name": "x", "address": "Fixture.nNest"}])  # address reused


def test_inventory_and_cli(export: list[Path], tmp_path: Path) -> None:
    inv = inventory(export)
    addresses = {a["address"] for a in inv["addresses"]}  # type: ignore[union-attr]
    assert any(a.endswith("StationA.bOk") for a in addresses)
    mapping_path = tmp_path / "mapping.json"
    mapping_path.write_text(_mapping().model_dump_json(), encoding="utf-8")
    assert (
        main(["convert", "--mapping", str(mapping_path), "--out", str(tmp_path / "cli"), *map(str, export)])
        == 0
    )
    assert (tmp_path / "cli" / "manifest.json").is_file()


def _read(out: Path):  # type: ignore[no-untyped-def]
    return read_pieces(
        out / "manifest.json",
        dataset_id="real-test",
        name="Test",
        description="d",
        max_bytes=10**7,
        max_pieces=10**6,
    )


def test_reader_builds_a_reported_basis_dataset(export: list[Path], tmp_path: Path) -> None:
    out = tmp_path / "dataset"
    convert(export, _mapping(), out, partitions=2)
    ds = _read(out)
    assert ds.source_type == "REAL" and ds.nok_basis == "reported" and len(ds) == 7
    assert ds.utc_offset_s == -300 * 60
    assert ds.primary_fail[2] == "st_b"  # P003 failed station B only
    assert [p.key for p in ds.presets] == ["b_by_nest"]
    assert ds.data_quality["empty_cycles_excluded"] == 1 and ds.data_quality["ids_provisional"] == 1

    result = overview(ds, QualityFilter())
    summary = result["summary"]
    assert summary["pieces"] == 7 and summary["nok_pieces"] == 1  # only P003 (C002 was re-inspected OK)
    assert result["pareto"] == [] and result["heatmap_axis"] == "station"
    assert result["station_pareto"][0] == {
        "station": "st_b",
        "name": "Estación B",
        "nok": 1,
        "fails_any": 1,
        "share": 1.0,
        "cumulative_pct": 1.0,
    }
    assert {r["cavity"] for r in result["by_mold_cavity"]} == {1, 2, 3}

    only_a = overview(ds, QualityFilter(stations=("st_a",)))
    assert only_a["summary"]["nok_pieces"] == 0
    clean = overview(ds, QualityFilter(exclude_flags=FLAG_REPEATED_SIGNATURE))
    assert clean["summary"]["pieces"] == 4

    detail = variable_detail(ds, QualityFilter(), "x1", "mold_cavity")
    assert detail["nok_basis"] == "reported" and "Estación A" in detail["nok_label"]
    assert detail["capability"]["cpk"] is None


def test_reader_refuses_tampered_files(export: list[Path], tmp_path: Path) -> None:
    out = tmp_path / "dataset"
    convert(export, _mapping(), out, partitions=1)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    manifest["pieces_sha256"] = "0" * 64
    (out / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        _read(out)
    with pytest.raises(ValueError, match="piece cap"):
        read_pieces(
            out / "manifest.json", dataset_id="x", name="x", description="x", max_bytes=10**7, max_pieces=2
        )
