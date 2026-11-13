"""Parse one station's daily CSV export into typed rows.

The station exports are `;`-separated, latin-1, one header row, timestamps
`YYYYMMDD-HH:MM:SS` in plant local time without offset. Columns are found by
their header names, so column order may change between machine software
versions. Positions above the product's pin count are filler and skipped.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

from app.ingest.config import StationConfig

# rMesswert values at or above this are the station's "no value" sentinel.
ELECTRICAL_SENTINEL = Decimal("1E14")
# Pin length result codes: 4 OK, 2 shorter, 1 longer, 0 not evaluated.
LENGTH_OK_CODE = 4
LENGTH_NOT_EVALUATED_CODE = 0

_FILE_DATE = re.compile(r"(\d{4})\.(\d{2})\.(\d{2})\.csv$")


class RowIssue(Exception):
    """A row that cannot be read; it is quarantined with this reason."""


@dataclass(frozen=True)
class ParsedValue:
    """One measured value. `measure` is the characteristic suffix
    (REF, P3, P3X, P3Y, M1-33-34, M1-33-34-V2)."""

    measure: str
    value: Decimal
    machine_ok: bool | None = None
    machine_code: int | None = None


@dataclass
class StationRow:
    """One piece at one station (electrical: the consecutive rows of one
    piece and timestamp, one value per tested point pair)."""

    row_number: int
    serial: str
    recorded_at: datetime
    nest: int | None
    program: int | None
    machine_ok: bool | None
    error_count: int | None = None
    reference_ok: bool | None = None
    values: list[ParsedValue] = field(default_factory=list)


@dataclass(frozen=True)
class BadRow:
    row_number: int
    raw: dict[str, str]
    reason: str


def file_day(path: Path) -> str | None:
    """`YYYY-MM-DD` from a daily file name, or None if it isn't one."""
    match = _FILE_DATE.search(path.name)
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}" if match else None


def station_files(data_dir: Path, station: StationConfig) -> list[Path]:
    """Daily files of a station, oldest first. Subfolders (calibration
    studies, copies) and non-daily files are not read."""
    folder = data_dir / station.folder
    if not folder.is_dir():
        return []
    files = [
        path
        for path in folder.iterdir()
        if path.is_file()
        and path.name.startswith(station.file_prefix)
        and file_day(path) is not None
        and path.name[len(station.file_prefix) :].count("_") == 0
    ]
    return sorted(files, key=lambda p: file_day(p) or "")


def parse_timestamp(text: str, tz: ZoneInfo) -> datetime:
    """`YYYYMMDD-HH:MM:SS` in plant local time. Ambiguous DST hours resolve to
    the first occurrence (fold=0)."""
    t = text.strip()
    if len(t) != 17 or t[8] != "-" or t[11] != ":" or t[14] != ":":
        raise RowIssue(f"Unreadable timestamp {t!r}.")
    try:
        return datetime(
            int(t[0:4]), int(t[4:6]), int(t[6:8]), int(t[9:11]), int(t[12:14]), int(t[15:17]), tzinfo=tz
        )
    except ValueError as exc:
        raise RowIssue(f"Unreadable timestamp {t!r}.") from exc


def _bool(text: str) -> bool | None:
    t = text.strip().lower()
    if t == "true":
        return True
    if t == "false":
        return False
    return None


def _int(text: str) -> int | None:
    t = text.strip().lstrip("+")
    if not t:
        return None
    try:
        return int(t)
    except ValueError:
        return None


def _decimal(text: str) -> Decimal | None:
    t = text.strip()
    if not t:
        return None
    try:
        value = Decimal(t)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


class _Columns:
    """Header name -> column index, with the station-specific lookups."""

    def __init__(self, header: list[str]) -> None:
        self.names = [h.strip().lstrip("﻿").lstrip("ï»¿") for h in header]
        self._index = {name: i for i, name in enumerate(self.names)}

    def find(self, prefix: str) -> int | None:
        for name, i in self._index.items():
            if name.startswith(prefix):
                return i
        return None

    def exact(self, name: str) -> int | None:
        return self._index.get(name)


def _cell(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return row[index]


@dataclass(frozen=True)
class _CommonColumns:
    program: int | None
    total_result: int | None


def _base(row: list[str], common: _CommonColumns, row_number: int, tz: ZoneInfo) -> StationRow:
    if len(row) < 3:
        raise RowIssue("Row has fewer columns than the header.")
    serial = row[1].strip()
    if not serial or serial.strip("0") == "":
        raise RowIssue("Missing piece id.")
    return StationRow(
        row_number=row_number,
        serial=serial,
        recorded_at=parse_timestamp(row[0], tz),
        nest=_int(row[2]),
        program=_int(_cell(row, common.program)) if common.program is not None else None,
        machine_ok=_bool(_cell(row, common.total_result)),
    )


@dataclass(frozen=True)
class _ValueColumn:
    """Where one measure's value and verdict live in a station file."""

    measure: str
    value: int
    verdict: int | None


def _value_columns(station: StationConfig, cols: _Columns, pins: int) -> list[_ValueColumn]:
    """Resolve the value columns of a station once per file."""
    plan: list[_ValueColumn] = []

    def add(measure: str, value_prefix: str, verdict_prefix: str) -> None:
        value_index = cols.find(value_prefix)
        if value_index is not None:
            plan.append(_ValueColumn(measure, value_index, cols.find(verdict_prefix)))

    if station.kind == "pin_length":
        add("REF", "Messwert Ref-MT1 ", "Ergebnis Ref-MT1 ")
        for n in range(1, pins + 1):
            add(f"P{n}", f"Messwert MT{n} ", f"Ergebnis MT{n} ")
    elif station.kind == "pin_position" and station.side == "connector":
        for n in range(1, pins + 1):
            for axis in ("X", "Y"):
                add(f"P{n}{axis}", f"Abweichung {n} {axis} ", f"Ergebnis {n} {axis} ")
    elif station.kind == "pin_position":
        for n in range(1, pins + 1):
            add(f"P{n}", f"Taumelkreis {n} ", f"Ergebnis {n} [")
    return plan


def _pin_length_values(row: list[str], plan: list[_ValueColumn], parsed: StationRow) -> None:
    for column in plan:
        value = _decimal(_cell(row, column.value))
        if value is None:
            continue
        code = _int(_cell(row, column.verdict))
        if code == LENGTH_NOT_EVALUATED_CODE and value == 0:
            continue  # position not evaluated by the station
        machine_ok = None if code is None or code == LENGTH_NOT_EVALUATED_CODE else code == LENGTH_OK_CODE
        parsed.values.append(ParsedValue(column.measure, value, machine_ok, code))


def _pin_position_values(row: list[str], plan: list[_ValueColumn], parsed: StationRow) -> None:
    for column in plan:
        value = _decimal(_cell(row, column.value))
        if value is not None:
            parsed.values.append(ParsedValue(column.measure, value, _bool(_cell(row, column.verdict))))


@dataclass(frozen=True)
class _ElectricalColumns:
    mess_type: int | None
    from_point: int | None
    to_point: int | None
    error_type: int | None
    error_count: int | None
    value1: int | None
    value2: int | None


def _electrical_columns(cols: _Columns) -> _ElectricalColumns:
    return _ElectricalColumns(
        cols.exact("iMessType"),
        cols.exact("iFromPoint"),
        cols.exact("iToPoint"),
        cols.exact("iFehlerType"),
        cols.exact("Anzahl Fehler"),
        cols.exact("rMesswert1"),
        cols.exact("rMesswert2"),
    )


def _electrical_values(row: list[str], ec: _ElectricalColumns, parsed: StationRow) -> None:
    mess_type = _int(_cell(row, ec.mess_type))
    from_point = _int(_cell(row, ec.from_point))
    to_point = _int(_cell(row, ec.to_point))
    if mess_type is None or from_point is None or to_point is None:
        raise RowIssue("Electrical row without measurement type or point pair.")
    parsed.error_count = _int(_cell(row, ec.error_count))
    code = _int(_cell(row, ec.error_type))
    measure = f"M{mess_type}-{from_point}-{to_point}"
    for suffix, index in (("", ec.value1), ("-V2", ec.value2)):
        value = _decimal(_cell(row, index))
        if value is not None and abs(value) < ELECTRICAL_SENTINEL:
            parsed.values.append(ParsedValue(measure + suffix, value, None, code))


def read_station_file(
    path: Path, station: StationConfig, pins: int, tz: ZoneInfo
) -> Iterator[StationRow | BadRow]:
    """Yield one StationRow per piece row (electrical: per piece and
    timestamp) or a BadRow for rows that cannot be read."""
    with path.open(encoding="latin-1", newline="") as handle:
        reader = csv.reader(handle, delimiter=";")
        header = next(reader, None)
        if header is None:
            return
        cols = _Columns(header)
        common = _CommonColumns(cols.exact("Programmnummer"), cols.find("Gesamtergebnis"))
        plan = _value_columns(station, cols, pins)
        electrical = _electrical_columns(cols)
        reference_col = cols.find("Ergebnis Referenz")
        pending: StationRow | None = None
        for row_number, row in enumerate(reader, start=2):
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            if row[0].strip() == cols.names[0]:
                continue  # repeated header
            try:
                parsed = _base(row, common, row_number, tz)
                if station.kind == "pin_length":
                    parsed.reference_ok = _bool(_cell(row, reference_col))
                    _pin_length_values(row, plan, parsed)
                elif station.kind == "pin_position":
                    _pin_position_values(row, plan, parsed)
                elif station.kind == "electrical":
                    _electrical_values(row, electrical, parsed)
            except RowIssue as issue:
                yield BadRow(row_number, dict(zip(cols.names, row, strict=False)), str(issue))
                continue

            if station.kind != "electrical":
                yield parsed
                continue
            if pending is not None and (pending.serial, pending.recorded_at) == (
                parsed.serial,
                parsed.recorded_at,
            ):
                pending.values.extend(parsed.values)
                continue
            if pending is not None:
                yield pending
            pending = parsed
        if pending is not None:
            yield pending


def read_type_check_programs(path: Path) -> Iterator[tuple[str, int | None]]:
    """Fast pass over a type-check file: (piece id, recipe) per row."""
    with path.open(encoding="latin-1", newline="") as handle:
        reader = csv.reader(handle, delimiter=";")
        header = next(reader, None)
        if header is None:
            return
        cols = _Columns(header)
        program_col = cols.exact("Programmnummer")
        for row in reader:
            if len(row) < 3 or row[0].strip() == cols.names[0]:
                continue
            serial = row[1].strip()
            if serial and serial.strip("0"):
                yield serial, _int(_cell(row, program_col))
