"""IQ-F10: offline batch converter for long "signal" exports -> one row per piece.

Some PLC data loggers export every value as its own row::

    id,address,timestamp,value
    <piece id>,<prefix>.<Station>.<signal>.[i],<timestamp>,<value>

A three-day export of such a line easily reaches tens of millions of rows,
far beyond the in-memory web import (IQ-F6). This module converts it offline,
on the operator's machine, into a compact per-piece file that the backend
loads at runtime (`app/connectors/pieces_file.py`):

- ``inventory`` lists the distinct addresses with counts and value kinds, to
  help write the mapping.
- ``convert`` applies a PRIVATE mapping (address -> role) and writes
  ``pieces.csv.gz`` + ``manifest.json``.

Bounded memory whatever the row order: pass 1 streams the files and spills
only the mapped rows into K hash partitions by piece id; pass 2 rebuilds the
pieces of one partition at a time; a final ordered merge writes the output.

Confidentiality (CLAUDE.md §7, plan decision D8): the mapping, the inventory
and the outputs are customer-specific and must live outside version control
(``demo-private/``). The converter never writes piece identifiers or source
paths, refuses an output directory inside the repository unless it is under
``demo-private/``, and drops unmapped addresses on read.

Pure stdlib + pydantic; no application settings are imported, so it runs
without any environment variable::

    python -m app.connectors.long_signal_batch inventory --out <dir>/inventory.json FILE...
    python -m app.connectors.long_signal_batch convert --mapping <dir>/mapping.json
        --out <dir>/dataset FILE...
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import heapq
import io
import json
import math
import re
import shutil
import sys
import tempfile
import zlib
from collections import Counter
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TextIO

from pydantic import BaseModel, Field, field_validator, model_validator

FORMAT = "pieces-v1"
CONVERTER_VERSION = "long-signal-batch-1.0.0"
DEFAULT_PARTITIONS = 32
MAX_MANIFEST_BYTES = 256 * 1024
MIN_SIGNATURE_VALUES = 3

# Per-piece quality flags (bit mask written in the ``flags`` column).
FLAG_SENTINEL = 1  # at least one value was a logger sentinel and became missing
FLAG_REPEATED_SIGNATURE = 2  # a station's full value set repeats suspiciously often
FLAG_GROUPING_OUT_OF_RANGE = 4  # nest / mold cavity outside the valid range

csv.field_size_limit(10 * 1024 * 1024)

_MONTHS = {
    m: i
    for i, m in enumerate(
        ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1
    )
}
# JavaScript ``Date.toString()``: "Mon Oct 19 2026 00:00:19 GMT-0500 (zone name)".
# Only the explicit numeric offset is trusted, never the zone name.
_JS_DATE = re.compile(
    r"^\s*[A-Za-z]{3}\s+([A-Za-z]{3})\s+(\d{1,2})\s+(\d{4})\s+(\d{2}):(\d{2}):(\d{2})\s+GMT([+-])(\d{2})(\d{2})"
)


# --------------------------------------------------------------------------- mapping


class _Verdict(BaseModel):
    address: str = Field(min_length=1, max_length=256)
    ok: list[str] = Field(default_factory=lambda: ["true"], min_length=1)
    nok: list[str] = Field(default_factory=lambda: ["false"], min_length=1)


class _Grouping(BaseModel):
    address: str = Field(min_length=1, max_length=256)
    valid: tuple[int, int]


class StationMap(_Verdict):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    name: str = Field(min_length=1, max_length=64)


class VariableMap(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    name: str = Field(min_length=1, max_length=64)
    unit: str = Field(default="", max_length=16)
    station: str | None = None
    address: str = Field(min_length=1, max_length=256)


class _IdKind(BaseModel):
    kind: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    pattern: str


class _EmptyCycle(BaseModel):
    """A piece is an empty/aborted cycle when this station failed AND every variable is 0 or missing."""

    station: str
    action: Literal["exclude"] = "exclude"


class _RepeatedSignature(BaseModel):
    min_repeats: int = Field(default=50, ge=2)


class _Preset(BaseModel):
    """A named filter shown as a shortcut in the UI (labels stay private)."""

    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    label: str = Field(min_length=1, max_length=64)
    stations: list[str] = Field(default_factory=list)
    group_by: Literal["nest", "mold_cavity"] = "nest"


class Mapping(BaseModel):
    """Private mapping: which addresses feed which role. Validated before any IO."""

    format: Literal["long-signals-v1"]
    columns: dict[Literal["id", "address", "timestamp", "value"], str] = Field(
        default_factory=lambda: {"id": "id", "address": "address", "timestamp": "timestamp", "value": "value"}
    )
    timestamp_format: Literal["js_date_string", "iso8601"] = "js_date_string"
    address_prefix: str = ""
    id_kinds: list[_IdKind] = Field(default_factory=list)
    nest: _Grouping
    mold_cavity: _Grouping | None = None
    total_verdict: _Verdict | None = None
    # Process order matters: the first failing station is the attributed cause.
    stations: list[StationMap] = Field(default_factory=list, max_length=24)
    variables: list[VariableMap] = Field(min_length=1, max_length=200)
    empty_cycle: _EmptyCycle | None = None
    sentinel_abs_min: float = 32000.0
    repeated_signature: _RepeatedSignature = Field(default_factory=_RepeatedSignature)
    presets: list[_Preset] = Field(default_factory=list, max_length=8)

    @field_validator("id_kinds")
    @classmethod
    def _compile(cls, kinds: list[_IdKind]) -> list[_IdKind]:
        for k in kinds:
            re.compile(k.pattern)
        return kinds

    @model_validator(mode="after")
    def _consistent(self) -> Mapping:
        station_keys = [s.key for s in self.stations]
        var_keys = [v.key for v in self.variables]
        if len(set(station_keys)) != len(station_keys) or len(set(var_keys)) != len(var_keys):
            raise ValueError("station and variable keys must be unique")
        for v in self.variables:
            if v.station is not None and v.station not in station_keys:
                raise ValueError(f"variable {v.key!r} references unknown station {v.station!r}")
        if self.empty_cycle is not None and self.empty_cycle.station not in station_keys:
            raise ValueError("empty_cycle.station must be a mapped station")
        for p in self.presets:
            if any(s not in station_keys for s in p.stations):
                raise ValueError(f"preset {p.key!r} references an unknown station")
        addresses = self.addresses()
        if len(set(addresses)) != len(addresses):
            raise ValueError("an address may feed only one role")
        return self

    def addresses(self) -> list[str]:
        """Every mapped address, in column order (the order used in partitions)."""
        out = [self.nest.address]
        if self.mold_cavity is not None:
            out.append(self.mold_cavity.address)
        if self.total_verdict is not None:
            out.append(self.total_verdict.address)
        out += [s.address for s in self.stations]
        out += [v.address for v in self.variables]
        return out


# --------------------------------------------------------------------------- parsing helpers


def parse_timestamp(text: str, fmt: str) -> tuple[int, int] | None:
    """Return (epoch milliseconds UTC, utc offset in minutes) or None if unparseable."""
    if fmt == "js_date_string":
        m = _JS_DATE.match(text)
        if m is None:
            return None
        mon = _MONTHS.get(m.group(1).lower())
        if mon is None:
            return None
        sign = 1 if m.group(7) == "+" else -1
        offset_min = sign * (int(m.group(8)) * 60 + int(m.group(9)))
        try:
            local = datetime(
                int(m.group(3)),
                mon,
                int(m.group(2)),
                int(m.group(4)),
                int(m.group(5)),
                int(m.group(6)),
                tzinfo=UTC,
            )
        except ValueError:
            return None
        return int(local.timestamp() * 1000) - offset_min * 60_000, offset_min
    try:
        dt = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return int(dt.replace(tzinfo=UTC).timestamp() * 1000), 0
    offset = dt.utcoffset()
    offset_min = int(offset.total_seconds() // 60) if offset is not None else 0
    return int(dt.timestamp() * 1000), offset_min


def _number(raw: str) -> float | None:
    s = raw.strip()
    if not s:
        return None
    try:
        x = float(s)
    except ValueError:
        return None
    return x if math.isfinite(x) else None


def _verdict(raw: str | None, ok: Sequence[str], nok: Sequence[str]) -> bool | None:
    """True = NOK, False = OK, None = missing/unknown."""
    if raw is None:
        return None
    s = raw.strip().lower()
    if s in nok:
        return True
    if s in ok:
        return False
    return None


def _open_text(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8-sig", newline="")
    return path.open("r", encoding="utf-8-sig", newline="")


@dataclass
class _ReadStats:
    files: int = 0
    rows_read: int = 0
    rows_valid: int = 0
    rows_mapped: int = 0
    malformed: Counter[str] = field(default_factory=Counter)
    unmapped_by_segment: Counter[str] = field(default_factory=Counter)
    offsets: Counter[int] = field(default_factory=Counter)


def _rows(
    files: Sequence[Path], mapping: Mapping, stats: _ReadStats
) -> Iterator[tuple[str, str, int, int, str]]:
    """Yield (id, address-without-prefix, ts_ms, seq, raw value) for every valid row."""
    cols: dict[str, str] = {str(k): v for k, v in mapping.columns.items()}
    prefix = mapping.address_prefix
    ts_cache: dict[str, tuple[int, int] | None] = {}
    seq = 0
    for path in files:
        stats.files += 1
        with _open_text(path) as fh:
            reader = csv.reader(fh)
            header = next(reader, None)
            if header is None:
                continue
            try:
                i_id, i_addr, i_ts, i_val = (
                    header.index(cols[k]) for k in ("id", "address", "timestamp", "value")
                )
            except ValueError as exc:
                raise ValueError(
                    "input file does not have the mapped id/address/timestamp/value columns"
                ) from exc
            width = len(header)
            for row in reader:
                stats.rows_read += 1
                seq += 1
                if len(row) != width:
                    stats.malformed["field_count"] += 1
                    continue
                pid = row[i_id].strip()
                if not pid:
                    stats.malformed["empty_id"] += 1
                    continue
                ts_text = row[i_ts]
                parsed = ts_cache.get(ts_text)
                if parsed is None and ts_text not in ts_cache:
                    parsed = parse_timestamp(ts_text, mapping.timestamp_format)
                    if len(ts_cache) < 2_000_000:
                        ts_cache[ts_text] = parsed
                if parsed is None:
                    stats.malformed["bad_timestamp"] += 1
                    continue
                stats.rows_valid += 1
                addr = row[i_addr]
                if prefix and addr.startswith(prefix):
                    addr = addr[len(prefix) :]
                stats.offsets[parsed[1]] += 1
                yield pid, addr, parsed[0], seq, row[i_val]


# --------------------------------------------------------------------------- inventory


def inventory(files: Sequence[Path], mapping: Mapping | None = None) -> dict[str, object]:
    """Distinct addresses with row counts and value kinds (numeric/bool/blank/text)."""
    fmt_mapping = mapping or Mapping.model_validate(
        {
            "format": "long-signals-v1",
            "nest": {"address": "_", "valid": [0, 0]},
            "variables": [{"key": "x", "name": "x", "address": "__"}],
        }
    )
    stats = _ReadStats()
    kinds: dict[str, Counter[str]] = {}
    ids: set[str] = set()
    for pid, addr, _ts, _seq, raw in _rows(files, fmt_mapping, stats):
        ids.add(pid)
        s = raw.strip().lower()
        kind = (
            "blank"
            if not s
            else "bool"
            if s in ("true", "false")
            else "numeric"
            if _number(s) is not None
            else "text"
        )
        kinds.setdefault(addr, Counter())[kind] += 1
    return {
        "files": stats.files,
        "rows_read": stats.rows_read,
        "rows_valid": stats.rows_valid,
        "malformed": dict(stats.malformed),
        "distinct_ids": len(ids),
        "utc_offsets_minutes": {str(k): v for k, v in sorted(stats.offsets.items())},
        "addresses": [
            {"address": a, "rows": sum(c.values()), "kinds": dict(c)} for a, c in sorted(kinds.items())
        ],
    }


# --------------------------------------------------------------------------- convert


@dataclass
class _ConvertStats:
    ids_total: int = 0
    id_kinds: Counter[str] = field(default_factory=Counter)
    pieces_written: int = 0
    empty_cycles_excluded: int = 0
    without_verdict: int = 0
    sentinels: Counter[str] = field(default_factory=Counter)
    grouping_out_of_range: Counter[str] = field(default_factory=Counter)
    grouping_missing: Counter[str] = field(default_factory=Counter)
    repeated_signature: Counter[str] = field(default_factory=Counter)
    reinspected: int = 0


def _partition_of(pid: str, k: int) -> int:
    return zlib.crc32(pid.encode("utf-8")) % k


def _spill(files: Sequence[Path], mapping: Mapping, tmp: Path, k: int, stats: _ReadStats) -> list[Path]:
    """Pass 1: keep only mapped rows, hash-partitioned by piece id into K gzip files."""
    col_of = {a: i for i, a in enumerate(mapping.addresses())}
    paths = [tmp / f"part-{i:03d}.csv.gz" for i in range(k)]
    handles = [
        io.TextIOWrapper(gzip.open(p, "wb", compresslevel=1), encoding="utf-8", newline="") for p in paths
    ]
    writers = [csv.writer(h) for h in handles]
    try:
        for pid, addr, ts, seq, raw in _rows(files, mapping, stats):
            col = col_of.get(addr)
            if col is None:
                seg = addr.split(".", 1)[0] if "." in addr else addr
                stats.unmapped_by_segment[seg[:48]] += 1
                continue
            stats.rows_mapped += 1
            writers[_partition_of(pid, k)].writerow((pid, col, ts, seq, raw))
    finally:
        for h in handles:
            h.close()
    return paths


@dataclass
class _Piece:
    ts_ms: int
    id_kind: str
    nest: int | None
    mold_cavity: int | None
    total_nok: bool | None
    stations: list[bool | None]
    flags: int
    values: list[float | None]
    signatures: list[str]  # one hash per station ("" = not eligible)


def _build_pieces(part: Path, mapping: Mapping, stats: _ConvertStats) -> list[_Piece]:
    """Pass 2 for one partition: last value per (id, column) by (ts, seq); piece ts = min ts."""
    n_cols = len(mapping.addresses())
    latest: dict[str, list[tuple[int, int, str] | None]] = {}
    first_ts: dict[str, int] = {}
    last_ts: dict[str, int] = {}
    with io.TextIOWrapper(gzip.open(part, "rb"), encoding="utf-8", newline="") as fh:
        for pid, col_s, ts_s, seq_s, raw in csv.reader(fh):
            col, ts, seq = int(col_s), int(ts_s), int(seq_s)
            slots = latest.get(pid)
            if slots is None:
                slots = latest[pid] = [None] * n_cols
                first_ts[pid] = ts
                last_ts[pid] = ts
            else:
                if ts < first_ts[pid]:
                    first_ts[pid] = ts
                if ts > last_ts[pid]:
                    last_ts[pid] = ts
            cur = slots[col]
            if cur is None or (ts, seq) > (cur[0], cur[1]):
                slots[col] = (ts, seq, raw)

    i_nest = 0
    i_cav = 1 if mapping.mold_cavity is not None else None
    i_total = (2 if mapping.mold_cavity is not None else 1) if mapping.total_verdict is not None else None
    i_st0 = 1 + (mapping.mold_cavity is not None) + (mapping.total_verdict is not None)
    i_var0 = i_st0 + len(mapping.stations)
    st_index = {s.key: j for j, s in enumerate(mapping.stations)}
    var_station = [st_index.get(v.station) if v.station is not None else None for v in mapping.variables]
    kinds = [(k.kind, re.compile(k.pattern)) for k in mapping.id_kinds]

    pieces: list[_Piece] = []
    for pid, piece_slots in latest.items():
        stats.ids_total += 1
        kind = next((name for name, rx in kinds if rx.fullmatch(pid)), "other")
        stats.id_kinds[kind] += 1
        if last_ts[pid] - first_ts[pid] > 10 * 60_000:
            stats.reinspected += 1

        def cell(i: int | None, slots: list[tuple[int, int, str] | None] = piece_slots) -> str | None:
            if i is None:
                return None
            entry = slots[i]
            return None if entry is None else entry[2]

        flags = 0

        def grouping(i: int | None, spec: _Grouping | None, name: str) -> int | None:
            nonlocal flags
            if i is None or spec is None:
                return None
            x = _number(cell(i) or "")
            if x is None:
                stats.grouping_missing[name] += 1
                return None
            v = int(x)
            if not (spec.valid[0] <= v <= spec.valid[1]):
                stats.grouping_out_of_range[name] += 1
                flags |= FLAG_GROUPING_OUT_OF_RANGE
                return None
            return v

        total = None
        if i_total is not None and mapping.total_verdict is not None:
            tv = mapping.total_verdict
            total = _verdict(cell(i_total), [t.lower() for t in tv.ok], [t.lower() for t in tv.nok])
        station_v = [
            _verdict(cell(i_st0 + j), [t.lower() for t in s.ok], [t.lower() for t in s.nok])
            for j, s in enumerate(mapping.stations)
        ]

        values: list[float | None] = []
        for j, v in enumerate(mapping.variables):
            x = _number(cell(i_var0 + j) or "")
            if x is not None and abs(x) >= mapping.sentinel_abs_min:
                stats.sentinels[v.key] += 1
                flags |= FLAG_SENTINEL
                x = None
            values.append(x)

        if mapping.empty_cycle is not None:
            j = st_index[mapping.empty_cycle.station]
            if station_v[j] is True and all(x is None or x == 0 for x in values):
                stats.empty_cycles_excluded += 1
                continue

        # Groupings are counted only for written pieces (empty cycles carry 0s).
        nest = grouping(i_nest, mapping.nest, "nest")
        cav = grouping(i_cav, mapping.mold_cavity, "mold_cavity")
        if total is None and all(s is None for s in station_v):
            stats.without_verdict += 1

        sigs: list[str] = []
        for j, _s in enumerate(mapping.stations):
            own = [values[i] for i, st in enumerate(var_station) if st == j]
            # Only multi-value stations: a single discrete value repeats naturally.
            if len(own) < MIN_SIGNATURE_VALUES or any(x is None for x in own) or all(x == 0 for x in own):
                sigs.append("")
            else:
                sigs.append(hashlib.blake2b(repr(own).encode(), digest_size=8).hexdigest())

        pieces.append(_Piece(first_ts[pid], kind, nest, cav, total, station_v, flags, values, sigs))
    pieces.sort(key=lambda p: p.ts_ms)
    return pieces


def _fmt_bool(v: bool | None) -> str:
    return "" if v is None else "1" if v else "0"


def _fmt_num(v: float | None) -> str:
    if v is None:
        return ""
    return str(int(v)) if v.is_integer() else repr(v)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _guard_output(out_dir: Path) -> None:
    """Refuse to write customer data inside a git checkout unless under demo-private/."""
    resolved = out_dir.resolve()
    for parent in (resolved, *resolved.parents):
        if (parent / ".git").exists():
            rel = resolved.relative_to(parent)
            if not rel.parts or rel.parts[0] != "demo-private":
                raise ValueError(
                    "output directory is inside a repository; use demo-private/ or a folder outside the repo"
                )
            return


def convert(
    files: Sequence[Path], mapping: Mapping, out_dir: Path, partitions: int = DEFAULT_PARTITIONS
) -> dict[str, object]:
    """Convert long signal exports into ``pieces.csv.gz`` + ``manifest.json``; return the manifest."""
    if partitions < 1:
        raise ValueError("partitions must be >= 1")
    _guard_output(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rstats = _ReadStats()
    cstats = _ConvertStats()
    tmp = Path(tempfile.mkdtemp(prefix=".convert-", dir=out_dir))
    try:
        parts = _spill(files, mapping, tmp, partitions, rstats)
        sorted_parts: list[Path] = []
        sig_counts: list[Counter[str]] = [Counter() for _ in mapping.stations]
        for i, part in enumerate(parts):
            pieces = _build_pieces(part, mapping, cstats)
            part.unlink()
            for p in pieces:
                for j, sig in enumerate(p.signatures):
                    if sig:
                        sig_counts[j][sig] += 1
            records = [
                (
                    p.ts_ms,
                    json.dumps(
                        [
                            p.ts_ms,
                            p.id_kind,
                            p.nest,
                            p.mold_cavity,
                            p.total_nok,
                            p.stations,
                            p.flags,
                            p.values,
                            p.signatures,
                        ]
                    ),
                )
                for p in pieces
            ]
            # Total order (ts, record) so the merged file is identical for any partition count.
            records.sort()
            sp = tmp / f"sorted-{i:03d}.json.gz"
            with gzip.open(sp, "wt", encoding="utf-8") as fh:
                for _ts, r in records:
                    fh.write(r)
                    fh.write("\n")
            sorted_parts.append(sp)

        threshold = mapping.repeated_signature.min_repeats
        pieces_path = out_dir / "pieces.csv.gz"
        header = ["ts_ms", "id_kind", "nest", "mold_cavity", "total_nok"]
        header += (
            [f"st_{s.key}" for s in mapping.stations] + ["flags"] + [f"v_{v.key}" for v in mapping.variables]
        )
        period = [None, None]
        with open(pieces_path, "wb") as raw_fh, gzip.GzipFile(fileobj=raw_fh, mode="wb", mtime=0) as gz:
            text = io.TextIOWrapper(gz, encoding="utf-8", newline="")
            w = csv.writer(text, lineterminator="\n")
            w.writerow(header)
            streams = [_iter_sorted(p) for p in sorted_parts]
            for _key, line in heapq.merge(*streams):
                ts, kind, nest, cav, total, stations, flags, values, sigs = json.loads(line)
                for j, sig in enumerate(sigs):
                    if sig and sig_counts[j][sig] >= threshold:
                        flags |= FLAG_REPEATED_SIGNATURE
                        cstats.repeated_signature[mapping.stations[j].key] += 1
                if period[0] is None:
                    period[0] = ts
                period[1] = ts
                row = [
                    str(ts),
                    kind,
                    "" if nest is None else str(nest),
                    "" if cav is None else str(cav),
                    _fmt_bool(total),
                ]
                row += [_fmt_bool(s) for s in stations] + [str(flags)] + [_fmt_num(v) for v in values]
                w.writerow(row)
                cstats.pieces_written += 1
            text.flush()
            text.detach()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    offset_mode = rstats.offsets.most_common(1)[0][0] if rstats.offsets else 0
    manifest: dict[str, object] = {
        "format": FORMAT,
        "converter_version": CONVERTER_VERSION,
        "mapping_sha256": hashlib.sha256(mapping.model_dump_json().encode()).hexdigest(),
        "pieces_file": "pieces.csv.gz",
        "pieces_sha256": _sha256(pieces_path),
        "pieces": cstats.pieces_written,
        "period_ms": period,
        "utc_offset_minutes": offset_mode,
        "utc_offsets_seen": sorted(rstats.offsets),
        "groupings": {
            "nest": list(mapping.nest.valid),
            "mold_cavity": list(mapping.mold_cavity.valid) if mapping.mold_cavity else None,
        },
        "has_total_verdict": mapping.total_verdict is not None,
        "stations": [{"key": s.key, "name": s.name} for s in mapping.stations],
        "variables": [
            {"key": v.key, "name": v.name, "unit": v.unit, "station": v.station} for v in mapping.variables
        ],
        "presets": [p.model_dump() for p in mapping.presets],
        "flags": {
            "sentinel": FLAG_SENTINEL,
            "repeated_signature": FLAG_REPEATED_SIGNATURE,
            "grouping_out_of_range": FLAG_GROUPING_OUT_OF_RANGE,
        },
        "report": {
            "files": rstats.files,
            "rows_read": rstats.rows_read,
            "rows_valid": rstats.rows_valid,
            "rows_mapped": rstats.rows_mapped,
            "malformed": dict(rstats.malformed),
            "unmapped_by_segment": dict(rstats.unmapped_by_segment.most_common(64)),
            "ids_total": cstats.ids_total,
            "id_kinds": dict(cstats.id_kinds),
            "empty_cycles_excluded": cstats.empty_cycles_excluded,
            "pieces_without_verdict": cstats.without_verdict,
            "sentinels": dict(cstats.sentinels),
            "grouping_out_of_range": dict(cstats.grouping_out_of_range),
            "grouping_missing": dict(cstats.grouping_missing),
            "repeated_signature_pieces": dict(cstats.repeated_signature),
            "repeated_signature_min_repeats": threshold,
            "reinspected_after_10_min": cstats.reinspected,
        },
    }
    body = json.dumps(manifest, ensure_ascii=False, indent=1)
    if len(body.encode("utf-8")) > MAX_MANIFEST_BYTES:
        raise ValueError("manifest exceeds 256 KB")
    (out_dir / "manifest.json").write_text(body, encoding="utf-8")
    return manifest


def _iter_sorted(path: Path) -> Iterator[tuple[int, str]]:
    """Yield (ts, raw record) -- the same total order the partitions were sorted with."""
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            raw = line.rstrip("\n")
            yield int(raw[1 : raw.index(",")]), raw


# --------------------------------------------------------------------------- CLI


def _load_mapping(path: Path) -> Mapping:
    return Mapping.model_validate_json(path.read_text(encoding="utf-8"))


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="long_signal_batch", description=__doc__.splitlines()[0] if __doc__ else None
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_inv = sub.add_parser("inventory", help="list distinct addresses with counts and value kinds")
    p_inv.add_argument("--out", type=Path, required=True)
    p_inv.add_argument("--mapping", type=Path, help="optional: only to read column names / timestamp format")
    p_inv.add_argument("files", type=Path, nargs="+")
    p_conv = sub.add_parser("convert", help="convert to pieces.csv.gz + manifest.json")
    p_conv.add_argument("--mapping", type=Path, required=True)
    p_conv.add_argument("--out", type=Path, required=True)
    p_conv.add_argument("--partitions", type=int, default=DEFAULT_PARTITIONS)
    p_conv.add_argument("files", type=Path, nargs="+")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.cmd == "inventory":
        _guard_output(args.out.parent)
        result = inventory(args.files, _load_mapping(args.mapping) if args.mapping else None)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"inventory: {len(result['addresses'])} addresses, {result['rows_valid']} valid rows")  # type: ignore[arg-type]
        return 0
    manifest = convert(args.files, _load_mapping(args.mapping), args.out, args.partitions)
    report = manifest["report"]
    print(f"convert: {manifest['pieces']} pieces written; report: {json.dumps(report)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
