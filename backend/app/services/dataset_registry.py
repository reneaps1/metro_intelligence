"""IQ-F21 (plan decisions D14, D15, D20, D22): registry of private datasets, one per part.

An operator converts each part's export offline into its own folder under the
private root ``DEMO_REAL_DATASETS_DIR``::

    <root>/<slug>/manifest.json        required (pieces-v1/v2 + optional F21 blocks)
    <root>/<slug>/pieces.csv.gz        the file the manifest points at
    <root>/<slug>/spec.json            optional pin-spec-v1 (X/Y view, IQ-F19)
    <root>/<slug>/report-summary.json  optional private report block (IQ-F5)
    <root>/<slug>/model-lab.json       optional private study results (IQ-F7)

Each valid folder becomes the selectable entry ``real-<slug>``. The catalog is
built from manifests only (cheap); pieces are loaded lazily on first use and
kept in a small LRU (``DEMO_REAL_DATASETS_MAX_LOADED``) because one part can
take a few hundred MB in memory. Invalid folders are skipped and only counted.

Nothing is offered unless `core.private_data.private_data_allowed()` holds, and
request input is only ever matched against the scanned ids: no path is built
from a request. Paths, file names and contents are never logged.

`resolve` is the single place every router uses to turn a dataset id into a
loaded dataset: synthetic -> legacy REAL (`real-dimensional`) -> registry ->
the caller's own in-memory import -> not found.
"""

from __future__ import annotations

import logging
import re
import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from app.connectors.pieces_file import Manifest, read_manifest, read_pieces
from app.core.config import get_settings
from app.core.private_data import private_data_allowed
from app.engines.quality_analytics.dataset import DimensionalDataset
from app.engines.quality_analytics.synthetic import SYNTHETIC_DATASET_ID, synthetic_dataset
from app.engines.quality_analytics.twins import build_twin, twin_meta, twin_spec
from app.services import dataset_cache, real_dataset_service
from app.services.imported_dataset_store import get_imported_dataset_store

logger = logging.getLogger(__name__)

REGISTRY_PREFIX = "real-"
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
# `real-dimensional` is the legacy single dataset (DEMO_REAL_DATASET_PATH).
RESERVED_SLUGS = frozenset({"dimensional"})
MAX_ENTRIES = 64
MANIFEST = "manifest.json"
SPEC_FILE = "spec.json"
EXTRA_FILES = frozenset({"report-summary.json", "model-lab.json"})
_MB = 1024 * 1024


class DatasetNotFoundError(LookupError):
    """The id is unknown, not offered here, or its files are unusable."""


@dataclass(frozen=True)
class Entry:
    """One selectable private dataset, described from its manifest only."""

    id: str
    folder: Path
    label: str
    line: str | None
    description: str
    order: int
    pieces: int
    period_start: datetime | None
    period_end: datetime | None
    process_join: bool
    group_labels: dict[str, str]
    assumptions: tuple[str, ...]
    signature: tuple[object, ...]

    @property
    def manifest_path(self) -> Path:
        return self.folder / MANIFEST


@dataclass(frozen=True)
class Catalog:
    entries: tuple[Entry, ...] = ()
    omitted: int = 0


@dataclass
class _Loaded:
    signature: tuple[object, ...]
    dataset: DimensionalDataset


_lock = threading.Lock()
_loaded: OrderedDict[str, _Loaded] = OrderedDict()


# --------------------------------------------------------------------------- scanning


def _stat(path: Path) -> tuple[int, int] | None:
    try:
        st = path.stat()
    except OSError:
        return None
    return (st.st_mtime_ns, st.st_size)


def _ms(value: int | None) -> datetime | None:
    return datetime.fromtimestamp(value / 1000, tz=UTC) if value else None


def _entry(folder: Path, manifest: Manifest) -> Entry:
    slug = folder.name
    display = manifest.display
    labels: dict[str, str] = {}
    if manifest.groups is not None:
        if manifest.groups.primary is not None:
            labels["primary"] = manifest.groups.primary.label
        if manifest.groups.secondary is not None:
            labels["secondary"] = manifest.groups.secondary.label
    window = manifest.window
    pieces_stat = _stat(folder / manifest.pieces_file)
    return Entry(
        id=f"{REGISTRY_PREFIX}{slug}",
        folder=folder,
        label=display.label if display else slug,
        line=display.line if display else None,
        description=(display.description if display and display.description else ""),
        order=display.order if display else 100,
        pieces=manifest.pieces,
        period_start=_ms(window.from_ms) if window else None,
        period_end=_ms(window.to_ms) if window else None,
        process_join=manifest.views.process_join,
        group_labels=labels,
        assumptions=tuple(manifest.assumptions),
        signature=(_stat(folder / MANIFEST), pieces_stat, _stat(folder / SPEC_FILE)),
    )


def scan() -> Catalog:
    """The current private catalog (manifests only). Empty when private data is not allowed."""
    settings = get_settings()
    root_value = settings.demo_real_datasets_dir
    if not root_value or not private_data_allowed(settings):
        return Catalog()
    root = Path(root_value)
    try:
        children = sorted(root.iterdir()) if root.is_dir() else []
    except OSError:
        logger.warning("The private datasets folder could not be listed; no part is offered from it.")
        return Catalog()
    entries: list[Entry] = []
    omitted = 0
    for child in children:
        if not child.is_dir():
            continue
        if len(entries) >= MAX_ENTRIES or not SLUG_PATTERN.match(child.name) or child.name in RESERVED_SLUGS:
            omitted += 1
            continue
        try:
            manifest = read_manifest(child / MANIFEST)
            if not (child / manifest.pieces_file).is_file():
                raise ValueError("pieces file missing")
        except (OSError, ValueError, ValidationError):
            omitted += 1
            continue
        entries.append(_entry(child, manifest))
    if omitted:
        logger.warning("%d private dataset folder(s) skipped as invalid.", omitted)
    entries.sort(key=lambda e: (e.order, e.label, e.id))
    return Catalog(tuple(entries), omitted)


def entry(dataset_id: str) -> Entry | None:
    if not dataset_id.startswith(REGISTRY_PREFIX):
        return None
    return next((e for e in scan().entries if e.id == dataset_id), None)


# --------------------------------------------------------------------------- loading


def is_loaded(dataset_id: str) -> bool:
    with _lock:
        return dataset_id in _loaded


def load(dataset_id: str) -> DimensionalDataset | None:
    """The dataset of a registry entry (lazy, LRU), or None when it is not offered or unusable."""
    found = entry(dataset_id)
    if found is None:
        return None
    settings = get_settings()
    evicted: list[str] = []
    with _lock:
        hit = _loaded.get(dataset_id)
        if hit is not None and hit.signature == found.signature:
            _loaded.move_to_end(dataset_id)
            return hit.dataset
        try:
            dataset = read_pieces(
                found.manifest_path,
                dataset_id=found.id,
                name=found.label,
                description=found.description
                or "Datos reales convertidos fuera de línea y cargados localmente. "
                "Veredictos OK/NOK reportados por la máquina.",
                max_bytes=settings.demo_real_dataset_max_mb * _MB,
                max_pieces=settings.demo_real_dataset_max_pieces,
            )
        except (OSError, ValueError, ValidationError):
            logger.warning("A private dataset could not be loaded; it is not offered.")
            return None
        spec = found.folder / SPEC_FILE
        if spec.is_file():
            real_dataset_service.attach_pin_spec(dataset, str(spec))
        if hit is not None:
            evicted.append(dataset_id)
        _loaded[dataset_id] = _Loaded(found.signature, dataset)
        _loaded.move_to_end(dataset_id)
        while len(_loaded) > settings.demo_real_datasets_max_loaded:
            old_id, _ = _loaded.popitem(last=False)
            evicted.append(old_id)
    for old_id in evicted:
        dataset_cache.forget(old_id)
    return dataset


def extra_path(dataset_id: str, name: str) -> Path | None:
    """A private side file of a registry entry (report summary, model lab), if present."""
    if name not in EXTRA_FILES:
        raise ValueError("unknown extra file")
    found = entry(dataset_id)
    if found is None:
        return None
    path = found.folder / name
    return path if path.is_file() else None


def initial_dataset_id() -> str | None:
    """The entry the selector opens with: the legacy REAL dataset, else the first registry entry."""
    if real_dataset_service.real_dataset_configured():
        return real_dataset_service.REAL_DATASET_ID
    entries = scan().entries
    return entries[0].id if entries else None


def warm_up_in_background() -> None:
    """Preload only the entry the selector opens with, off the request path."""
    target = initial_dataset_id()
    if target is None:
        return
    loader = (
        real_dataset_service.load_real_dataset
        if target == real_dataset_service.REAL_DATASET_ID
        else (lambda: load(target))
    )
    threading.Thread(target=loader, name="dataset-warmup", daemon=True).start()


def reset_cache() -> None:
    """Tests only."""
    with _lock:
        ids = list(_loaded)
        _loaded.clear()
    for dataset_id in ids:
        dataset_cache.forget(dataset_id)


# --------------------------------------------------------------------------- resolution


def resolve(
    dataset_id: str,
    owner_id: uuid.UUID | None = None,
    *,
    allow_imports: bool = True,
) -> DimensionalDataset:
    """The one lookup every router uses. Raises `DatasetNotFoundError`."""
    if dataset_id == SYNTHETIC_DATASET_ID:
        return synthetic_dataset()
    twin = twin_spec(dataset_id)
    if twin is not None:
        return build_twin(twin.slug)
    if dataset_id == real_dataset_service.REAL_DATASET_ID:
        real = real_dataset_service.load_real_dataset()
        if real is not None:
            return real
        raise DatasetNotFoundError(dataset_id)
    if dataset_id.startswith(REGISTRY_PREFIX):
        loaded = load(dataset_id)
        if loaded is not None:
            return loaded
        raise DatasetNotFoundError(dataset_id)
    if allow_imports and owner_id is not None:
        stored = get_imported_dataset_store().get(dataset_id, owner_id)
        if stored is not None:
            return stored.dataset
    raise DatasetNotFoundError(dataset_id)


def is_private(dataset_id: str) -> bool:
    return dataset_id == real_dataset_service.REAL_DATASET_ID or dataset_id.startswith(REGISTRY_PREFIX)


def process_join_enabled(ds: DimensionalDataset) -> bool:
    """D27: Vista A stays on for the legacy dataset and is opt-in (manifest `views`) for the others."""
    if ds.source_type != "REAL":
        return False
    if ds.id == real_dataset_service.REAL_DATASET_ID:
        return True
    found = entry(ds.id)
    return bool(found and found.process_join)


@dataclass(frozen=True)
class Meta:
    """Selector metadata of a dataset that `DimensionalDataset` does not carry."""

    line: str | None = None
    group_labels: dict[str, str] = field(default_factory=dict)
    assumptions: tuple[str, ...] = ()
    process_join: bool = False


def meta(ds: DimensionalDataset) -> Meta:
    twin = twin_meta(ds.id)
    if twin is not None:
        line, labels, assumptions = twin
        return Meta(line, labels, assumptions, False)
    if ds.id == real_dataset_service.REAL_DATASET_ID:
        return Meta(process_join=ds.source_type == "REAL")
    found = entry(ds.id)
    if found is None:
        return Meta()
    return Meta(found.line, dict(found.group_labels), found.assumptions, found.process_join)
