"""IQ-F6: dimensional CSV adapter (detection, mapping, validation, sampling)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.connectors.base import FileValidationError
from app.connectors.dimensional_csv import (
    ColumnMapping,
    MappingError,
    VariableSpec,
    build_dataset,
    decode,
    detect_decimal,
    detect_delimiter,
    parse_number,
    parse_timestamp,
    parse_verdict,
    sniff,
    trim_partial_line,
)
from app.engines.quality_analytics import QualityFilter, overview, variable_detail

SAMPLES = Path(__file__).resolve().parents[2] / "seed" / "sample_files"

LONG_CSV = """Fecha;Hora;Pieza;Nido;Variable;Valor;LIE;LSE;Resultado
01/09/2026;06:00:00;P1;Nido 1;A;1,00;0,90;1,10;OK
01/09/2026;06:00:00;P1;Nido 1;B;5,00;;5,20;OK
01/09/2026;06:10:00;P2;Nido 2;A;1,20;0,90;1,10;NOK
01/09/2026;06:10:00;P2;Nido 2;B;5,10;;5,20;NOK
01/09/2026;06:20:00;P3;Nido 3;A;abc;0,90;1,10;OK
01/09/2026;06:20:00;P3;Nido 3;B;;;5,20;OK
32/13/2026;06:30:00;P4;Nido 1;A;1,00;0,90;1,10;OK
01/09/2026;06:10:00;P2;Nido 2;A;1,05;0,90;1,10;OK
"""

WIDE_CSV = """timestamp,serial,cavity,result,H,W
2026-09-15T07:00:00-06:00,S1,CAV-01,PASS,2.50,0.80
2026-09-15T07:01:00-06:00,S2,CAV-02,FAIL,2.60,0.80
2026-09-15T07:02:00-06:00,S3,CAV-01,PASS,2.49,
2026-09-15T07:03:00-06:00,S4,CAV-02,PASS,ERR,0.81
2026-09-15T07:04:00-06:00,S5,CAV-01,PASS,,
2026-09-15T07:05:00-06:00,S1,CAV-01,PASS,2.50,0.80
"""


def _long_mapping(**overrides: object) -> ColumnMapping:
    base: dict[str, object] = dict(
        layout="long",
        timestamp="Fecha",
        time="Hora",
        piece_id="Pieza",
        cavity="Nido",
        variable="Variable",
        value="Valor",
        lsl="LIE",
        usl="LSE",
        ok_nok="Resultado",
    )
    base.update(overrides)
    return ColumnMapping(**base)  # type: ignore[arg-type]


def _build(text: str, mapping: ColumnMapping, delimiter: str, decimal: str = ".", **kw: object):
    return build_dataset(
        text,
        delimiter=delimiter,
        decimal=decimal,
        mapping=mapping,
        dataset_id="t",
        name="t",
        **{"max_rows": 1000, **kw},  # type: ignore[arg-type]
    )


# --- low-level parsing ---------------------------------------------------------


@pytest.mark.parametrize("delimiter", [",", ";", "\t", "|"])
def test_delimiter_detection(delimiter: str) -> None:
    text = "\n".join(delimiter.join(row) for row in [["a", "b", "c"], ["1", "2", "3"], ["4", "5", "6"]])
    assert detect_delimiter(text) == delimiter


def test_semicolon_file_with_decimal_commas_is_not_read_as_comma_separated() -> None:
    assert detect_delimiter(LONG_CSV) == ";"
    assert detect_decimal([["1,00", "0,90"], ["5,10", "x"]], ";") == ","
    assert detect_decimal([["1.00", "0.90"]], ";") == "."
    assert detect_decimal([["1,00"]], ",") == "."


def test_parse_number() -> None:
    assert parse_number("-0,031", ",") == pytest.approx(-0.031)
    assert parse_number("1.234,5", ",") == pytest.approx(1234.5)
    assert parse_number("12.034", ",") == pytest.approx(12.034)  # no comma -> dot is decimal
    assert parse_number(" 2.5 ", ".") == pytest.approx(2.5)
    for bad in ("", "abc", "nan", "inf"):
        assert parse_number(bad, ".") is None


def test_parse_timestamp_formats() -> None:
    ref = datetime(2026, 9, 1, 6, 0, tzinfo=UTC).timestamp()
    assert parse_timestamp("2026-09-01T06:00:00Z", "dmy") == (ref, True)
    assert parse_timestamp("2026-09-01 00:00:00-06:00", "dmy") == (ref, True)
    assert parse_timestamp("01/09/2026", "dmy", "06:00") == (ref, False)
    assert parse_timestamp("09/01/2026 06:00:00", "mdy") == (ref, False)
    assert parse_timestamp(str(int(ref * 1000)), "dmy") == (ref, True)
    assert parse_timestamp("31/02/2026", "dmy") is None
    assert parse_timestamp("", "dmy") is None


def test_parse_verdict() -> None:
    assert [parse_verdict(v) for v in ("NOK", "n.i.O.", "FAIL", "Rechazado")] == [True] * 4
    assert [parse_verdict(v) for v in ("ok", "i.O.", "PASS", "Aceptado")] == [False] * 4
    assert parse_verdict("1") is None


def test_encoding_fallback_and_binary_rejection() -> None:
    text, encoding = decode("Característica;Valor\nAltura;1,0\n".encode("cp1252"))
    assert encoding == "cp1252" and text.startswith("Característica")
    assert decode("﻿a,b\n1,2\n".encode())[1] == "utf-8"
    with pytest.raises(FileValidationError):
        decode(b"MZ\x90\x00binary")
    with pytest.raises(FileValidationError):
        decode(b"")


def test_trim_partial_line_cuts_at_last_newline_in_bytes() -> None:
    head = "a,b\n1,ñ\n2,ñ".encode()[:-1]  # cut inside the last multi-byte char
    assert trim_partial_line(head) == "a,b\n1,ñ\n".encode()


# --- preview -------------------------------------------------------------------


def test_sniff_long_layout_suggests_roles() -> None:
    result = sniff(LONG_CSV.encode())
    assert (result.delimiter, result.decimal, result.date_order) == (";", ",", "dmy")
    s = result.suggestion
    assert s.layout == "long"
    assert s.roles == {
        "timestamp": "Fecha",
        "time": "Hora",
        "piece_id": "Pieza",
        "cavity": "Nido",
        "ok_nok": "Resultado",
        "variable": "Variable",
        "value": "Valor",
        "lsl": "LIE",
        "usl": "LSE",
    }
    kinds = {p.name: p.kind for p in result.profiles}
    assert kinds["Valor"] == "number"  # one broken cell does not hide a numeric column
    assert kinds["Fecha"] == "datetime"
    assert result.rows[0][0] == "01/09/2026"


def test_sniff_wide_layout_suggests_value_columns() -> None:
    s = sniff(WIDE_CSV.encode()).suggestion
    assert s.layout == "wide"
    assert s.roles["timestamp"] == "timestamp" and s.roles["cavity"] == "cavity"
    assert s.value_columns == ["H", "W"]


def test_sniff_rejects_formula_injection() -> None:
    with pytest.raises(FileValidationError, match="injection"):
        sniff(b'a,b\n1,=HYPERLINK("x")\n')
    # a negative decimal-comma number is data, not a payload
    assert sniff(b"a;b\n1;-0,03\n").decimal == ","


# --- long layout ---------------------------------------------------------------


def test_long_layout_pivots_to_canonical_pieces_and_quarantines() -> None:
    ds, report = _build(LONG_CSV, _long_mapping(), ";", ",")
    assert ds is not None
    assert report.rows_read == 8
    assert report.rows_accepted == 4
    assert dict(report.quarantine_counts) == {
        "Valor no numérico": 1,
        "Valor vacío (nulo)": 1,
        "Fecha/hora vacía o no reconocida": 1,
        "Duplicado (misma pieza y variable)": 1,
    }
    assert report.empty_values == 1
    assert len(ds) == 2  # P1, P2 (P3 lost both rows)
    assert ds.cavities == [1, 2]
    assert [v.key for v in ds.variables] == ["A", "B"]
    a, b = ds.variables
    assert (a.lsl, a.usl, a.display_nominal) == (pytest.approx(0.9), pytest.approx(1.1), None)
    assert (b.lsl, b.usl) == (None, pytest.approx(5.2))
    assert ds.values["A"] == [pytest.approx(1.0), pytest.approx(1.2)]
    assert ds.nok["A"] == [False, True]
    assert ds.reported_nok == [False, True]
    assert ds.source_type == "IMPORTED"
    assert "UTC" in report.warnings[0]


def test_units_must_match_within_a_variable() -> None:
    text = "t;v;x;u\n2026-01-01T00:00:00Z;A;1;mm\n2026-01-01T00:01:00Z;A;2;in\n2026-01-01T00:02:00Z;A;3;mm\n"
    ds, report = _build(
        text, ColumnMapping(layout="long", timestamp="t", variable="v", value="x", unit="u"), ";"
    )
    assert ds is not None and len(ds) == 2
    assert report.quarantine_counts == {"Unidad distinta a la del resto de la variable": 1}
    assert ds.variables[0].unit == "mm"


def test_typed_spec_overrides_file_limits_and_bad_limits_are_dropped() -> None:
    mapping = _long_mapping(specs={"A": VariableSpec(nominal=1.0, lsl=0.95, usl=1.25)})
    ds, _ = _build(LONG_CSV, mapping, ";", ",")
    assert ds is not None
    a = ds.variable("A")
    assert (a.display_nominal, a.lsl, a.usl) == (1.0, pytest.approx(0.95), pytest.approx(1.25))
    assert ds.nok["A"] == [False, False]

    _, report = _build(LONG_CSV, _long_mapping(specs={"B": VariableSpec(lsl=6.0, usl=5.0)}), ";", ",")
    assert any("LIE > LSE" in w for w in report.warnings)


# --- wide layout ---------------------------------------------------------------


def test_wide_layout_one_row_per_piece() -> None:
    mapping = ColumnMapping(
        layout="wide",
        timestamp="timestamp",
        piece_id="serial",
        cavity="cavity",
        ok_nok="result",
        value_columns=("H", "W"),
    )
    ds, report = _build(WIDE_CSV, mapping, ",")
    assert ds is not None
    assert len(ds) == 3
    assert dict(report.quarantine_counts) == {
        "Valor no numérico en una columna de variable": 1,
        "Fila sin valores (todas las variables vacías)": 1,
        "Pieza duplicada": 1,
    }
    assert ds.values["W"] == [pytest.approx(0.8), pytest.approx(0.8), None]  # empty cell stays a null
    assert ds.reported_nok == [False, True, False]
    assert not any(v.has_tolerance for v in ds.variables)
    assert any("Ninguna variable tiene tolerancias" in w for w in report.warnings)
    # without tolerances there is no spec NOK and no capability
    o = overview(ds, QualityFilter())
    assert o["summary"]["nok_pieces"] == 0 and o["summary"]["worst_cavity"] is None
    assert o["summary"]["source_reported"]["nok_pieces"] == 1
    assert variable_detail(ds, QualityFilter(), "H")["capability"]["cpk"] is None


# --- mapping validation ----------------------------------------------------------


@pytest.mark.parametrize(
    ("mapping", "message"),
    [
        (ColumnMapping(layout="long", timestamp="Nope", variable="Variable", value="Valor"), "no existe"),
        (ColumnMapping(layout="long", timestamp="Fecha"), "variable"),
        (ColumnMapping(layout="wide", timestamp="Fecha"), "al menos una"),
        (
            ColumnMapping(layout="long", timestamp="Fecha", variable="Variable", value="Variable"),
            "dos campos",
        ),
        (ColumnMapping(layout="wide", timestamp="Fecha", value_columns=("Fecha",)), "otro campo"),
    ],
)
def test_mapping_errors(mapping: ColumnMapping, message: str) -> None:
    with pytest.raises(MappingError, match=message):
        _build(LONG_CSV, mapping, ";", ",")


# --- sampling ------------------------------------------------------------------


def test_row_cap_produces_a_labelled_sample() -> None:
    lines = ["t,x"] + [f"2026-01-01T00:{i // 60:02d}:{i % 60:02d}Z,{i}" for i in range(1000)]
    text = "\n".join(lines) + "\n"
    mapping = ColumnMapping(layout="wide", timestamp="t", value_columns=("x",))
    ds, report = _build(text, mapping, ",", max_rows=100)
    assert ds is not None and len(ds) == 100
    assert report.sample_limited
    assert report.approx_file_fraction == pytest.approx(0.1, abs=0.02)

    _, full = _build(text, mapping, ",")
    assert not full.sample_limited and full.approx_file_fraction is None


def test_truncated_head_scales_the_file_fraction() -> None:
    text = "t,x\n2026-01-01T00:00:00Z,1\n2026-01-01T00:00:01Z,2\n"
    mapping = ColumnMapping(layout="wide", timestamp="t", value_columns=("x",))
    _, report = _build(text, mapping, ",", truncated=True, sent_fraction=0.25)
    assert report.sample_limited and report.approx_file_fraction == pytest.approx(0.25)


# --- versioned fixtures ----------------------------------------------------------


def test_long_fixture_round_trip() -> None:
    content = (SAMPLES / "mi_demo_dimensional_long.csv").read_bytes()
    preview = sniff(content)
    s = preview.suggestion
    mapping = ColumnMapping(layout=s.layout, date_order=preview.date_order, **s.roles)  # type: ignore[arg-type]
    ds, report = _build(decode(content)[0], mapping, preview.delimiter, preview.decimal, max_rows=200_000)
    assert ds is not None
    assert len(ds) == 960 and len(ds.variables) == 6 and ds.cavities.count(11) == 60
    assert report.rows_quarantined == 5 and len(report.quarantine_counts) == 5
    summary = overview(ds, QualityFilter())["summary"]
    assert summary["worst_cavity"]["cavity"] == 11
    reported = summary["source_reported"]
    assert reported["source_only_nok"] > 0  # tighter in-house flatness limit in the source verdict


def test_wide_fixture_round_trip() -> None:
    content = (SAMPLES / "mi_demo_dimensional_wide.csv").read_bytes()
    preview = sniff(content)
    s = preview.suggestion
    mapping = ColumnMapping(layout="wide", value_columns=tuple(s.value_columns), **s.roles)  # type: ignore[arg-type]
    ds, report = _build(decode(content)[0], mapping, preview.delimiter, preview.decimal, max_rows=200_000)
    assert ds is not None
    assert len(ds) == 1197 and ds.cavities[0] == 1 and set(ds.batches) == {"LOT-M1", "LOT-M2"}
    assert report.rows_quarantined == 3
