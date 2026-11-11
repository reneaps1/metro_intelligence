"""IQ-F10: read the per-piece file written by `long_signal_batch` into a dataset.

The manifest is validated first (format, sizes, declared columns) and the
pieces file must match its SHA-256, so a truncated or edited file is refused
instead of being analysed silently. Values are parsed with the stdlib only;
identical value strings share one float object, which keeps a few hundred
thousand pieces x a few dozen variables within a modest memory budget.

Pure: the caller decides the dataset id, name and size caps.

Formats: ``pieces-v1`` (IQ-F10) and ``pieces-v2`` (IQ-F17), which adds the raw
nest / mold cavity next to the normalized ones.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.engines.quality_analytics.dataset import DimensionalDataset, Preset, Station, Variable

MAX_MANIFEST_BYTES = 256 * 1024


class _StationIn(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    name: str = Field(min_length=1, max_length=64)


class _VariableIn(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    name: str = Field(min_length=1, max_length=64)
    unit: str = Field(default="", max_length=16)
    station: str | None = None


class _PresetIn(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    label: str = Field(min_length=1, max_length=64)
    stations: list[str] = Field(default_factory=list)
    group_by: Literal["nest", "mold_cavity"] = "nest"


class DisplayIn(BaseModel):
    """IQ-F21: how a dataset is named in the part selector (labels written by the operator)."""

    label: str = Field(min_length=1, max_length=64)
    line: str | None = Field(default=None, max_length=64)
    description: str | None = Field(default=None, max_length=280)
    order: int = Field(default=100, ge=0, le=10_000)


class GroupLabelIn(BaseModel):
    label: str = Field(min_length=1, max_length=32)
    prefix: str = Field(default="", max_length=4)
    values: dict[str, str] = Field(default_factory=dict, max_length=64)


class GroupsIn(BaseModel):
    """IQ-F21: vocabulary of the two grouping slots (`nest` = primary, `mold_cavity` = secondary)."""

    primary: GroupLabelIn | None = None
    secondary: GroupLabelIn | None = None


class WindowIn(BaseModel):
    """IQ-F21: which part of the source the converter kept (epoch ms; counts only)."""

    from_ms: int = Field(ge=0)
    to_ms: int = Field(ge=0)
    source_pieces: int = Field(ge=0)


class HistoryIn(BaseModel):
    """IQ-F21: aggregated daily history of the whole source, next to the loaded window."""

    granularity: Literal["day"] = "day"
    columns: list[Literal["day", "pieces", "nok"]] = Field(default_factory=lambda: ["day", "pieces", "nok"])
    rows: list[list[str | int]] = Field(default_factory=list, max_length=2_000)


class ViewsIn(BaseModel):
    """IQ-F21 (D27): opt-in views. Vista A joins simulated injection signals, so it is off by default."""

    process_join: bool = False


class Manifest(BaseModel):
    format: Literal["pieces-v1", "pieces-v2"]
    converter_version: str = Field(max_length=64)
    # A plain file name next to the manifest: no leading dot (so never ".." or a hidden file).
    pieces_file: str = Field(pattern=r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}$")
    pieces_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pieces: int = Field(ge=1)
    utc_offset_minutes: int = Field(ge=-14 * 60, le=14 * 60)
    has_total_verdict: bool
    stations: list[_StationIn] = Field(max_length=24)
    variables: list[_VariableIn] = Field(min_length=1, max_length=200)
    presets: list[_PresetIn] = Field(default_factory=list, max_length=8)
    report: dict[str, object] = Field(default_factory=dict)
    # --- IQ-F21: optional blocks, backwards compatible (older manifests omit them) ---
    display: DisplayIn | None = None
    groups: GroupsIn | None = None
    time_basis: Literal["utc", "plant_wall_clock"] | None = None
    window: WindowIn | None = None
    history: HistoryIn | None = None
    views: ViewsIn = Field(default_factory=ViewsIn)
    assumptions: list[str] = Field(default_factory=list, max_length=12)


def read_manifest(manifest_path: Path) -> Manifest:
    """Validate a manifest without touching the pieces file (cheap: used to list datasets)."""
    if manifest_path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("manifest too large")
    manifest = Manifest.model_validate(json.loads(manifest_path.read_text(encoding="utf-8")))
    if any(len(a) > 280 for a in manifest.assumptions):
        raise ValueError("assumption text too long")
    return manifest


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sum(value: object) -> int:
    if isinstance(value, dict):
        return sum(int(v) for v in value.values() if isinstance(v, int))
    return int(value) if isinstance(value, int) else 0


def _sum_nested(value: object) -> int:
    """Sum a {grouping: {"13->1": n}} report (or a flat count dict)."""
    if isinstance(value, dict):
        return sum(_sum(v) for v in value.values())
    return _sum(value)


def data_quality_counts(report: dict[str, object]) -> dict[str, int]:
    """Counts only -- never identifiers, paths or address names."""
    malformed = report.get("malformed", {})
    id_kinds = report.get("id_kinds", {})
    counts = {
        "rows_valid": _sum(report.get("rows_valid")),
        "rows_malformed": _sum(malformed),
        "ids_total": _sum(report.get("ids_total")),
        "empty_cycles_excluded": _sum(report.get("empty_cycles_excluded")),
        "pieces_without_verdict": _sum(report.get("pieces_without_verdict")),
        "sentinel_values": _sum(report.get("sentinels")),
        "grouping_out_of_range": _sum(report.get("grouping_out_of_range")),
        "grouping_remapped": _sum_nested(report.get("grouping_remapped")),
        "repeated_signature_pieces": _sum(report.get("repeated_signature_pieces")),
        "reinspected_after_10_min": _sum(report.get("reinspected_after_10_min")),
    }
    if isinstance(id_kinds, dict):
        for kind, n in id_kinds.items():
            if isinstance(n, int) and str(kind).isidentifier():
                counts[f"ids_{str(kind)[:24]}"] = n
    return counts


def read_pieces(
    manifest_path: Path,
    *,
    dataset_id: str,
    name: str,
    description: str,
    max_bytes: int,
    max_pieces: int,
    source_type: Literal["REAL", "SIMULATED"] = "REAL",
) -> DimensionalDataset:
    """Load a converted dataset. Raises ValueError / OSError / ValidationError when unusable.

    ``source_type`` is decided by the caller from WHERE the folder lives (the
    private root = REAL, files shipped with the app = SIMULATED), never by the
    manifest itself (IQ-F21, D23).
    """
    manifest = read_manifest(manifest_path)
    if manifest.pieces > max_pieces:
        raise ValueError("dataset exceeds the configured piece cap")
    pieces_path = manifest_path.parent / manifest.pieces_file
    if pieces_path.stat().st_size > max_bytes:
        raise ValueError("pieces file exceeds the configured size cap")
    if _sha256(pieces_path) != manifest.pieces_sha256:
        raise ValueError("pieces file does not match the manifest checksum")

    station_keys = [s.key for s in manifest.stations]
    var_keys = [v.key for v in manifest.variables]
    v2 = manifest.format == "pieces-v2"
    expected = ["ts_ms", "id_kind", "nest", "mold_cavity"]
    expected += ["nest_raw", "mold_cavity_raw"] if v2 else []
    expected += ["total_nok"]
    expected += [f"st_{k}" for k in station_keys] + ["flags"] + [f"v_{k}" for k in var_keys]
    # Column of the total verdict: 4 in v1, 6 in v2 (after the two raw groupings).
    c_total = 6 if v2 else 4

    memo: dict[str, float] = {}
    timestamps: list[float] = []
    nests: list[int | None] = []
    molds: list[int | None] = []
    nests_raw: list[int | None] = []
    molds_raw: list[int | None] = []
    total: list[bool | None] = []
    flags: list[int] = []
    st_cols: list[list[bool | None]] = [[] for _ in station_keys]
    var_cols: list[list[float | None]] = [[] for _ in var_keys]
    verdict = {"": None, "1": True, "0": False}

    with io.TextIOWrapper(gzip.open(pieces_path, "rb"), encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        if next(reader, None) != expected:
            raise ValueError("pieces file columns do not match the manifest")
        n_st = len(station_keys)
        for row in reader:
            if len(row) != len(expected):
                raise ValueError("malformed row in pieces file")
            timestamps.append(int(row[0]) / 1000)
            nests.append(int(row[2]) if row[2] else None)
            molds.append(int(row[3]) if row[3] else None)
            if v2:
                nests_raw.append(int(row[4]) if row[4] else None)
                molds_raw.append(int(row[5]) if row[5] else None)
            total.append(verdict[row[c_total]])
            for j in range(n_st):
                st_cols[j].append(verdict[row[c_total + 1 + j]])
            flags.append(int(row[c_total + 1 + n_st]))
            base = c_total + 2 + n_st
            for j, col in enumerate(var_cols):
                raw = row[base + j]
                if not raw:
                    col.append(None)
                    continue
                x = memo.get(raw)
                if x is None:
                    x = memo[raw] = float(raw)
                col.append(x)
    n = len(timestamps)
    if n != manifest.pieces:
        raise ValueError("piece count does not match the manifest")
    if any(b < a for a, b in zip(timestamps, timestamps[1:], strict=False)):
        raise ValueError("pieces file is not sorted by time")

    stations = tuple(Station(s.key, s.name) for s in manifest.stations)
    station_nok = dict(zip(station_keys, st_cols, strict=True))
    if manifest.has_total_verdict:
        reported: list[bool | None] = [
            t
            if t is not None
            else (any(c[i] for c in st_cols) if any(c[i] is not None for c in st_cols) else None)
            for i, t in enumerate(total)
        ]
    else:
        reported = [
            any(c[i] for c in st_cols) if any(c[i] is not None for c in st_cols) else None for i in range(n)
        ]
    absent: list[str | None] = [None] * n
    return DimensionalDataset(
        id=dataset_id,
        name=name,
        description=description,
        source_type=source_type,
        variables=tuple(
            Variable(v.key, v.name, v.unit, 0.0, None, None, nominal_given=False, station=v.station)
            for v in manifest.variables
        ),
        timestamps=timestamps,
        group_ids=list(range(n)),
        machines=absent,
        cavities=nests,
        shifts=absent,
        batches=absent,
        values=dict(zip(var_keys, var_cols, strict=True)),
        reported_nok=reported,
        # IQ-F21: a line without a secondary grouping has none at all (not a column of blanks),
        # so the views that need it are hidden instead of drawn empty.
        mold_cavities=molds if any(m is not None for m in molds) else None,
        nests_raw=nests_raw if v2 else None,
        mold_cavities_raw=molds_raw if v2 else None,
        stations=stations,
        station_nok=station_nok,
        flags=flags,
        utc_offset_s=manifest.utc_offset_minutes * 60,
        nok_basis="reported",
        has_groups=False,
        presets=tuple(Preset(p.key, p.label, tuple(p.stations), p.group_by) for p in manifest.presets),
        data_quality={"pieces": n, **data_quality_counts(manifest.report)},
    )
