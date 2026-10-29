"""IQ-F6: dimensional CSV adapter -- any column layout -> `DimensionalDataset`.

The F4.5 manual-upload connector only accepts the catalog's fixed wide format
(`COL_<balloon>` columns) and writes immutable measurement history. Real
inspection exports rarely look like that, so this adapter turns an arbitrary
CSV into the source-agnostic dimensional dataset that the quality analytics
already aggregate, driven by an explicit column mapping:

- ``sniff()`` reads the head of a file: encoding, delimiter, decimal mark,
  inferred column types and a suggested mapping (never trusted blindly --
  the user confirms it).
- ``build_dataset()`` applies a mapping in *long* (one row per measurement)
  or *wide* (one row per piece, one column per variable) layout, validates
  every row and quarantines the bad ones with a reason, never dropping them
  silently (CLAUDE.md §6). Large files are analysed as a capped sample.

Pure: no database, no storage, no evaluation of cell content. The same
hardening as ``manual_upload`` applies -- binary signatures and
formula-injection payloads reject the whole file.
"""

from __future__ import annotations

import csv
import io
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from app.connectors.base import FileValidationError
from app.connectors.manual_upload import _BINARY_SIGNATURES, _UNCONDITIONAL_FORMULA_TRIGGERS
from app.engines.quality_analytics.dataset import DimensionalDataset, Variable

Layout = Literal["long", "wide"]
DateOrder = Literal["ymd", "dmy", "mdy"]

DELIMITERS = (",", ";", "\t", "|")
PREVIEW_ROWS = 20
PROFILE_ROWS = 500
MAX_COLUMNS = 300
MAX_VARIABLES = 200
MAX_LABEL_LENGTH = 64
QUARANTINE_EXAMPLES = 50
KIND_QUORUM = 0.8
# Plausible measurement dates; anything outside is a parsing problem, not data.
MIN_PLAUSIBLE = datetime(1990, 1, 1, tzinfo=UTC).timestamp()
MAX_FUTURE_S = 24 * 3600

ColumnKind = Literal["number", "integer", "datetime", "text", "empty"]

# Verdict tokens, compared after normalisation (lowercase, no accents/punctuation).
_NOK_TOKENS = {
    "nok",
    "nio",
    "ng",
    "fail",
    "failed",
    "rechazado",
    "rechazada",
    "malo",
    "mala",
    "bad",
    "reject",
    "notok",
}
_OK_TOKENS = {"ok", "io", "pass", "passed", "aceptado", "aceptada", "bueno", "buena", "good", "accept"}

_DMY = re.compile(
    r"^(\d{1,4})[/.\-](\d{1,2})[/.\-](\d{1,4})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2})(?:[.,](\d{1,6}))?)?)?$"
)
_TIME = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2})(?:[.,](\d{1,6}))?)?$")
_DIGITS = re.compile(r"(\d+)")


class MappingError(ValueError):
    """The mapping does not fit the file. The message is safe to show as-is."""


# --------------------------------------------------------------------------- #
# Low-level parsing
# --------------------------------------------------------------------------- #


def _normalise(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", folded.lower())


def decode(content: bytes) -> tuple[str, str]:
    """Return (text, encoding). UTF-8 (with or without BOM) first, then the
    Windows-1252 code page most spreadsheet exports in Spanish use."""
    if not content:
        raise FileValidationError("File is empty.")
    if any(content.startswith(sig) for sig in _BINARY_SIGNATURES) or b"\x00" in content[:4096]:
        raise FileValidationError("File content does not look like a valid CSV file.")
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text, encoding = content.decode("latin-1"), "latin-1"
    sample = text[:4096]
    printable = sum(1 for ch in sample if ch.isprintable() or ch in "\r\n\t")
    if sample and printable / len(sample) < 0.85:
        raise FileValidationError("File content does not look like a valid CSV file.")
    return text, "utf-8" if encoding == "utf-8-sig" else encoding


def trim_partial_line(content: bytes) -> bytes:
    """Drop the (probably cut) last line of a file head. Works on bytes so a
    multi-byte character split by the cut never reaches the decoder."""
    cut = max(content.rfind(b"\n"), content.rfind(b"\r"))
    return content[: cut + 1] if cut > 0 else content


def detect_delimiter(text: str) -> str:
    """The candidate that splits the first lines into the most, and the most
    consistent, number of fields."""
    lines = [line for line in text.splitlines()[:50] if line.strip()]
    if not lines:
        raise FileValidationError("File is empty.")
    best, best_score = ",", 0.0
    for delimiter in DELIMITERS:
        counts = [len(row) for row in csv.reader(lines, delimiter=delimiter)]
        width, freq = Counter(counts).most_common(1)[0]
        if width < 2:
            continue
        score = width * (freq / len(counts))
        if score > best_score:
            best, best_score = delimiter, score
    return best


def parse_number(raw: str, decimal: str) -> float | None:
    s = raw.strip().replace(" ", "")
    if not s:
        return None
    if decimal == ",":
        s = s.replace(".", "").replace(",", ".") if "," in s else s
    try:
        value = float(s)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def detect_decimal(rows: list[list[str]], delimiter: str) -> str:
    if delimiter == ",":
        return "."
    comma = dot = 0
    for row in rows:
        for cell in row:
            c = cell.strip()
            if re.fullmatch(r"-?\d+,\d+", c):
                comma += 1
            elif re.fullmatch(r"-?\d+\.\d+", c):
                dot += 1
    return "," if comma > dot else "."


def parse_timestamp(
    raw: str, date_order: DateOrder, time_raw: str | None = None
) -> tuple[float, bool] | None:
    """Return (epoch seconds, had_timezone) or None if unparseable.

    Accepts ISO 8601, epoch seconds/milliseconds and D/M/Y or M/D/Y dates
    (with an optional separate time column). Naive values are read as UTC
    -- the caller warns about it.
    """
    s = raw.strip()
    if time_raw is not None and time_raw.strip():
        s = f"{s} {time_raw.strip()}"
    if not s:
        return None
    if re.fullmatch(r"\d{9,13}(\.\d+)?", s):
        value = float(s)
        return (value / 1000 if value > 1e11 else value), True
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        dt = None
    if dt is None:
        m = _DMY.match(s)
        if not m:
            return None
        a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if len(m.group(1)) == 4:
            year, month, day = a, b, c
        elif date_order == "mdy":
            month, day, year = a, b, c
        else:
            day, month, year = a, b, c
        if year < 100:
            year += 2000
        frac = m.group(7) or "0"
        try:
            dt = datetime(
                year,
                month,
                day,
                int(m.group(4) or 0),
                int(m.group(5) or 0),
                int(m.group(6) or 0),
                int(frac.ljust(6, "0")[:6]),
            )
        except ValueError:
            return None
    had_tz = dt.tzinfo is not None
    if not had_tz:
        dt = dt.replace(tzinfo=UTC)
    return dt.timestamp(), had_tz


def parse_verdict(raw: str) -> bool | None:
    """True = NOK, False = OK, None = not a recognised verdict."""
    token = _normalise(raw)
    if token in _NOK_TOKENS:
        return True
    if token in _OK_TOKENS:
        return False
    return None


def _formula_injection(cell: str, decimal: str) -> bool:
    if not cell:
        return False
    if cell.startswith(_UNCONDITIONAL_FORMULA_TRIGGERS):
        return True
    return cell.startswith("-") and parse_number(cell, decimal) is None


def _read_rows(text: str, delimiter: str) -> tuple[list[str], Iterator[list[str]], io.StringIO]:
    buffer = io.StringIO(text, newline="")
    reader = csv.reader(buffer, delimiter=delimiter)
    try:
        raw_header = next(reader)
    except StopIteration:
        raise FileValidationError("File is empty.") from None
    if len(raw_header) > MAX_COLUMNS:
        raise FileValidationError(f"Too many columns (max {MAX_COLUMNS}).")
    header: list[str] = []
    seen: Counter[str] = Counter()
    for i, name in enumerate(raw_header):
        clean = name.strip()[:MAX_LABEL_LENGTH] or f"col_{i + 1}"
        seen[clean] += 1
        header.append(clean if seen[clean] == 1 else f"{clean}_{seen[clean]}")
    return header, reader, buffer


# --------------------------------------------------------------------------- #
# Preview / sniffing
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ColumnProfile:
    name: str
    kind: ColumnKind
    non_empty: int
    examples: list[str]


@dataclass(frozen=True)
class SuggestedMapping:
    layout: Layout
    roles: dict[str, str]  # role -> column
    value_columns: list[str]


@dataclass(frozen=True)
class SniffResult:
    encoding: str
    delimiter: str
    decimal: str
    header: list[str]
    rows: list[list[str]]
    profiles: list[ColumnProfile]
    suggestion: SuggestedMapping
    date_order: DateOrder
    sampled_rows: int


_ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    "timestamp": (
        "fechahora",
        "datetime",
        "timestamp",
        "fecha",
        "date",
        "measuredat",
        "runat",
        "zeitstempel",
    ),
    "time": ("hora", "time", "uhrzeit"),
    "piece_id": (
        "idpieza",
        "pieza",
        "pieceid",
        "piece",
        "serial",
        "serie",
        "numerodeserie",
        "dmc",
        "barcode",
        "partid",
    ),
    "group": ("ciclo", "cycle", "disparo", "shot", "grupo", "group", "inyeccion", "idciclo", "cycleid"),
    "cavity": ("nido", "cavidad", "cavity", "nest", "cav"),
    "machine": ("maquina", "machine", "prensa", "press", "linea", "line"),
    "shift": ("turno", "shift", "schicht"),
    "batch": ("lote", "batch", "lot", "lotematerial", "materiallot"),
    "ok_nok": (
        "resultado",
        "result",
        "oknok",
        "estado",
        "status",
        "veredicto",
        "judgement",
        "evaluacion",
        "bewertung",
    ),
    "variable": ("variable", "caracteristica", "characteristic", "cota", "feature", "dimension", "merkmal"),
    "value": ("valor", "value", "medicion", "measured", "measurement", "medido", "istwert", "valormedido"),
    "nominal": ("nominal", "nom", "sollwert"),
    "lsl": ("lie", "lsl", "lower", "limiteinferior", "tolinf", "lowerlimit", "lei", "min"),
    "usl": ("lse", "usl", "upper", "limitesuperior", "tolsup", "upperlimit", "les", "max"),
    "unit": ("unidad", "unit", "uom", "einheit"),
}
_NUMERIC_ROLES = {"value", "nominal", "lsl", "usl"}


def _kind(values: list[str], decimal: str) -> ColumnKind:
    cells = [v.strip() for v in values if v.strip()]
    if not cells:
        return "empty"
    # Majority rule: a few broken cells must not hide a numeric column --
    # they are exactly what the quarantine is for.
    quorum = max(1, math.ceil(len(cells) * KIND_QUORUM))
    numbers = [(parse_number(c, decimal), c) for c in cells]
    parsed = [(n, c) for n, c in numbers if n is not None]
    if len(parsed) >= quorum:
        if all(n.is_integer() and "." not in c and "," not in c for n, c in parsed):
            return "integer"
        return "number"
    if sum(1 for c in cells if parse_timestamp(c, "dmy") is not None or _TIME.match(c)) >= quorum:
        return "datetime"
    return "text"


def _guess_date_order(values: list[str]) -> DateOrder:
    for v in values:
        m = _DMY.match(v.strip())
        if m and len(m.group(1)) <= 2:
            if int(m.group(1)) > 12:
                return "dmy"
            if int(m.group(2)) > 12:
                return "mdy"
    return "dmy"


def _suggest(header: list[str], profiles: list[ColumnProfile]) -> SuggestedMapping:
    kind = {p.name: p.kind for p in profiles}
    roles: dict[str, str] = {}
    used: set[str] = set()
    normalised = {col: _normalise(col) for col in header}
    for role, aliases in _ROLE_ALIASES.items():
        for alias in aliases:  # alias order = priority
            match = next(
                (
                    col
                    for col in header
                    if col not in used
                    and normalised[col] == alias
                    and (role not in _NUMERIC_ROLES or kind[col] in ("number", "integer"))
                    and (role != "timestamp" or kind[col] in ("datetime", "integer"))
                ),
                None,
            )
            if match:
                roles[role] = match
                used.add(match)
                break
    layout: Layout = "long" if "variable" in roles and "value" in roles else "wide"
    if layout == "wide":
        for role in ("variable", "value", "nominal", "lsl", "usl", "unit"):
            if role in roles:
                used.discard(roles.pop(role))
    value_columns = [c for c in header if c not in used and kind[c] == "number"] if layout == "wide" else []
    return SuggestedMapping(layout=layout, roles=roles, value_columns=value_columns)


def sniff(content: bytes, delimiter: str | None = None) -> SniffResult:
    """Profile a file head. ``delimiter`` overrides detection (user's choice)."""
    text, encoding = decode(content)
    if delimiter is None:
        delimiter = detect_delimiter(text)
    elif delimiter not in DELIMITERS:
        raise FileValidationError("Unsupported delimiter.")
    header, reader, _ = _read_rows(text, delimiter)
    rows: list[list[str]] = []
    for row in reader:
        if not any(cell.strip() for cell in row):
            continue
        rows.append(row)
        if len(rows) >= PROFILE_ROWS:
            break
    decimal = detect_decimal(rows, delimiter)
    for row in rows:
        if any(_formula_injection(cell, decimal) for cell in row):
            raise FileValidationError("File rejected: possible formula/command injection.")
    columns = [[row[i] if i < len(row) else "" for row in rows] for i in range(len(header))]
    profiles = [
        ColumnProfile(
            name=name,
            kind=_kind(col, decimal),
            non_empty=sum(1 for v in col if v.strip()),
            examples=list(dict.fromkeys(v.strip()[:MAX_LABEL_LENGTH] for v in col if v.strip()))[:5],
        )
        for name, col in zip(header, columns, strict=True)
    ]
    suggestion = _suggest(header, profiles)
    ts_col = suggestion.roles.get("timestamp")
    date_order = _guess_date_order(columns[header.index(ts_col)]) if ts_col else "dmy"
    return SniffResult(
        encoding=encoding,
        delimiter=delimiter,
        decimal=decimal,
        header=header,
        rows=[row[: len(header)] for row in rows[:PREVIEW_ROWS]],
        profiles=profiles,
        suggestion=suggestion,
        date_order=date_order,
        sampled_rows=len(rows),
    )


# --------------------------------------------------------------------------- #
# Mapping -> dataset
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class VariableSpec:
    """Specification typed by the user (overrides limits found in the file)."""

    nominal: float | None = None
    lsl: float | None = None
    usl: float | None = None
    unit: str | None = None


@dataclass(frozen=True)
class ColumnMapping:
    layout: Layout
    timestamp: str
    time: str | None = None
    date_order: DateOrder = "dmy"
    piece_id: str | None = None
    group: str | None = None
    cavity: str | None = None
    machine: str | None = None
    shift: str | None = None
    batch: str | None = None
    ok_nok: str | None = None
    # long layout
    variable: str | None = None
    value: str | None = None
    nominal: str | None = None
    lsl: str | None = None
    usl: str | None = None
    unit: str | None = None
    # wide layout
    value_columns: tuple[str, ...] = ()
    # keyed by variable name (long) or value column (wide)
    specs: dict[str, VariableSpec] = field(default_factory=dict)

    def validate(self, header: list[str]) -> None:
        known = set(header)
        singles = {
            "fecha/hora": self.timestamp,
            "hora": self.time,
            "ID de pieza": self.piece_id,
            "ciclo": self.group,
            "nido": self.cavity,
            "máquina": self.machine,
            "turno": self.shift,
            "lote": self.batch,
            "OK/NOK": self.ok_nok,
            "variable": self.variable,
            "valor": self.value,
            "nominal": self.nominal,
            "LIE": self.lsl,
            "LSE": self.usl,
            "unidad": self.unit,
        }
        for role, col in singles.items():
            if col is not None and col not in known:
                raise MappingError(f"La columna «{col}» ({role}) no existe en el archivo.")
        missing = [c for c in self.value_columns if c not in known]
        if missing:
            raise MappingError(f"La columna «{missing[0]}» no existe en el archivo.")
        used = [c for c in singles.values() if c is not None]
        if len(used) != len(set(used)):
            raise MappingError("Una misma columna está asignada a dos campos.")
        if self.layout == "long":
            if not self.variable or not self.value:
                raise MappingError("Formato largo: asigna las columnas «variable» y «valor».")
            if self.value_columns:
                raise MappingError("Formato largo: no se usan columnas de valor por variable.")
        else:
            if not self.value_columns:
                raise MappingError("Formato ancho: elige al menos una columna de variable.")
            if len(self.value_columns) > MAX_VARIABLES:
                raise MappingError(f"Máximo {MAX_VARIABLES} variables.")
            if any(c in used for c in self.value_columns) or len(set(self.value_columns)) != len(
                self.value_columns
            ):
                raise MappingError("Una columna de variable también está asignada a otro campo.")
            if any(
                c is not None
                for c in (self.variable, self.value, self.nominal, self.lsl, self.usl, self.unit)
            ):
                raise MappingError(
                    "Formato ancho: variable/valor/límites por fila solo aplican al formato largo."
                )


@dataclass
class _Piece:
    ts: float
    group: str | None
    cavity: str | None
    machine: str | None
    shift: str | None
    batch: str | None
    values: dict[str, float]
    verdicts: list[bool]


@dataclass
class BuildReport:
    layout: Layout
    rows_read: int = 0
    rows_accepted: int = 0
    pieces: int = 0
    variables: int = 0
    empty_values: int = 0
    quarantine_counts: Counter[str] = field(default_factory=Counter)
    quarantine_examples: list[tuple[int, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sample_limited: bool = False
    approx_file_fraction: float | None = None
    naive_timestamps: bool = False

    @property
    def rows_quarantined(self) -> int:
        return sum(self.quarantine_counts.values())

    def quarantine(self, row_number: int, reason: str) -> None:
        self.quarantine_counts[reason] += 1
        if len(self.quarantine_examples) < QUARANTINE_EXAMPLES:
            self.quarantine_examples.append((row_number, reason))


def _label(raw: str) -> str | None:
    s = raw.strip()[:MAX_LABEL_LENGTH]
    return s or None


def _slug(name: str, taken: set[str]) -> str:
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    base = re.sub(r"[^A-Za-z0-9_\-]+", "_", folded).strip("_")[:48] or "var"
    key, n = base, 2
    while key in taken:
        key, n = f"{base}_{n}", n + 1
    taken.add(key)
    return key


def build_dataset(
    text: str,
    *,
    delimiter: str,
    decimal: str,
    mapping: ColumnMapping,
    max_rows: int,
    dataset_id: str,
    name: str,
    truncated: bool = False,
    sent_fraction: float = 1.0,
) -> tuple[DimensionalDataset | None, BuildReport]:
    """Apply ``mapping`` to ``text``. ``truncated`` = ``text`` is only the head
    of a larger file (already cut at a line end, see ``trim_partial_line``);
    ``sent_fraction`` = bytes analysed / file size, for the sample notice."""
    header, reader, buffer = _read_rows(text, delimiter)
    mapping.validate(header)
    col = {name: i for i, name in enumerate(header)}
    report = BuildReport(layout=mapping.layout)

    def cell(row: list[str], column: str | None) -> str:
        return row[col[column]] if column is not None else ""

    pieces: dict[object, _Piece] = {}
    seen_long: set[tuple[object, str]] = set()
    file_specs: dict[str, VariableSpec] = {}
    units_seen: dict[str, str] = {}
    conflicting_specs: set[str] = set()
    cavity_unparsed = 0
    max_ts = datetime.now(tz=UTC).timestamp() + MAX_FUTURE_S

    for row_number, row in enumerate(reader, start=1):
        if not any(c.strip() for c in row):
            continue
        if report.rows_read >= max_rows:
            report.sample_limited = True
            break
        report.rows_read += 1
        if any(_formula_injection(c, decimal) for c in row):
            raise FileValidationError("File rejected: possible formula/command injection.")
        if len(row) != len(header):
            report.quarantine(row_number, "Número de columnas distinto al encabezado")
            continue
        parsed = parse_timestamp(
            cell(row, mapping.timestamp),
            mapping.date_order,
            cell(row, mapping.time) if mapping.time else None,
        )
        if parsed is None:
            report.quarantine(row_number, "Fecha/hora vacía o no reconocida")
            continue
        ts, had_tz = parsed
        if not MIN_PLAUSIBLE <= ts <= max_ts:
            report.quarantine(row_number, "Fecha fuera de rango plausible")
            continue
        report.naive_timestamps |= not had_tz
        verdict = parse_verdict(cell(row, mapping.ok_nok)) if mapping.ok_nok else None
        context = (
            _label(cell(row, mapping.group)),
            _label(cell(row, mapping.cavity)),
            _label(cell(row, mapping.machine)),
            _label(cell(row, mapping.shift)),
            _label(cell(row, mapping.batch)),
        )
        piece_raw = _label(cell(row, mapping.piece_id)) if mapping.piece_id else None

        if mapping.layout == "long":
            var_name = _label(cell(row, mapping.variable))
            if var_name is None:
                report.quarantine(row_number, "Variable vacía")
                continue
            raw_value = cell(row, mapping.value)
            if not raw_value.strip():
                report.empty_values += 1
                report.quarantine(row_number, "Valor vacío (nulo)")
                continue
            value = parse_number(raw_value, decimal)
            if value is None:
                report.quarantine(row_number, "Valor no numérico")
                continue
            unit = _label(cell(row, mapping.unit)) if mapping.unit else None
            if unit is not None:
                first_unit = units_seen.setdefault(var_name, unit)
                if unit != first_unit:
                    report.quarantine(row_number, "Unidad distinta a la del resto de la variable")
                    continue
            key: object = piece_raw if piece_raw is not None else (ts, context[1], context[2])
            if (key, var_name) in seen_long:
                report.quarantine(row_number, "Duplicado (misma pieza y variable)")
                continue
            if var_name not in file_specs and len(file_specs) >= MAX_VARIABLES:
                raise MappingError(f"El archivo tiene más de {MAX_VARIABLES} variables distintas.")
            spec = VariableSpec(
                nominal=parse_number(cell(row, mapping.nominal), decimal) if mapping.nominal else None,
                lsl=parse_number(cell(row, mapping.lsl), decimal) if mapping.lsl else None,
                usl=parse_number(cell(row, mapping.usl), decimal) if mapping.usl else None,
                unit=unit,
            )
            known_spec = file_specs.setdefault(var_name, spec)
            if (known_spec.nominal, known_spec.lsl, known_spec.usl) != (spec.nominal, spec.lsl, spec.usl):
                conflicting_specs.add(var_name)
            seen_long.add((key, var_name))
            piece = pieces.get(key)
            if piece is None:
                piece = pieces[key] = _Piece(ts, *context, values={}, verdicts=[])
            piece.ts = min(piece.ts, ts)
            piece.values[var_name] = value
            if verdict is not None:
                piece.verdicts.append(verdict)
        else:
            if piece_raw is not None and piece_raw in pieces:
                report.quarantine(row_number, "Pieza duplicada")
                continue
            values: dict[str, float] = {}
            bad_column = None
            for column in mapping.value_columns:
                raw_value = cell(row, column)
                if not raw_value.strip():
                    report.empty_values += 1
                    continue
                value = parse_number(raw_value, decimal)
                if value is None:
                    bad_column = column
                    break
                values[column] = value
            if bad_column is not None:
                report.quarantine(row_number, "Valor no numérico en una columna de variable")
                continue
            if not values:
                report.quarantine(row_number, "Fila sin valores (todas las variables vacías)")
                continue
            pieces[piece_raw if piece_raw is not None else ("row", row_number)] = _Piece(
                ts, *context, values=values, verdicts=[] if verdict is None else [verdict]
            )
        report.rows_accepted += 1

    if report.sample_limited or truncated:
        consumed = buffer.tell() / len(text) if text else 1.0
        report.approx_file_fraction = min(1.0, consumed * sent_fraction)
        report.sample_limited = True
    if report.naive_timestamps:
        report.warnings.append("Fechas sin zona horaria: se interpretaron como UTC.")
    for var_name in sorted(conflicting_specs):
        report.warnings.append(
            f"«{var_name}» trae límites distintos en distintas filas; se usan los de la primera."
        )

    if not pieces:
        return None, report

    # --- variables ---
    names = list(file_specs) if mapping.layout == "long" else list(mapping.value_columns)
    taken: set[str] = set()
    variables: list[Variable] = []
    key_of: dict[str, str] = {}
    for var_name in names:
        from_file = file_specs.get(var_name, VariableSpec())
        typed = mapping.specs.get(var_name)
        spec = from_file if typed is None else typed
        unit = (typed.unit if typed and typed.unit else None) or from_file.unit or ""
        lsl, usl = spec.lsl, spec.usl
        if lsl is not None and usl is not None and lsl > usl:
            report.warnings.append(f"«{var_name}»: LIE > LSE; se ignoran sus tolerancias.")
            lsl = usl = None
        key = _slug(var_name, taken)
        key_of[var_name] = key
        variables.append(
            Variable.from_limits(key, var_name[:MAX_LABEL_LENGTH], unit[:16], spec.nominal, lsl, usl)
        )
    if not any(v.has_tolerance for v in variables):
        report.warnings.append(
            "Ninguna variable tiene tolerancias: no hay NOK por especificación ni Cp/Cpk; "
            "solo se muestran distribuciones y el OK/NOK de la fuente si existe."
        )

    # --- columns ---
    ordered = sorted(pieces.values(), key=lambda p: p.ts)
    group_index: dict[str, int] = {}
    group_ids: list[int] = []
    cavities: list[int | None] = []
    for i, p in enumerate(ordered):
        group_ids.append(group_index.setdefault(p.group, len(group_index)) if p.group is not None else i)
        if p.cavity is None:
            cavities.append(None)
        else:
            digits = _DIGITS.findall(p.cavity)
            cavities.append(int(digits[-1]) if digits else None)
            cavity_unparsed += not digits
    if cavity_unparsed:
        report.warnings.append(f"{cavity_unparsed} piezas con nido sin número reconocible: quedan sin nido.")

    report.pieces = len(ordered)
    report.variables = len(variables)
    dataset = DimensionalDataset(
        id=dataset_id,
        name=name,
        description=(
            f"Archivo importado ({'formato largo' if mapping.layout == 'long' else 'formato ancho'}): "
            f"{report.pieces:,} piezas × {report.variables} "
            f"variable{'s' if report.variables != 1 else ''}. No verificado por la plataforma."
        ),
        source_type="IMPORTED",
        variables=tuple(variables),
        timestamps=[p.ts for p in ordered],
        group_ids=group_ids,
        machines=[p.machine for p in ordered],
        cavities=cavities,
        shifts=[p.shift for p in ordered],
        batches=[p.batch for p in ordered],
        values={key_of[n]: [p.values.get(n) for p in ordered] for n in names},
        reported_nok=[any(p.verdicts) if p.verdicts else None for p in ordered] if mapping.ok_nok else None,
    )
    return dataset, report
