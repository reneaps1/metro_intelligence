"""IQ-F10: the customer's REAL dimensional dataset, loaded locally at runtime.

Plan decision D8: real customer data never lives in the repository nor on a
shared server. An operator converts the export offline
(`app/connectors/long_signal_batch.py`) into a private folder and points
`DEMO_REAL_DATASET_PATH` at its ``manifest.json``. Unset, missing, invalid or
in production = the dataset is simply not offered (the demo keeps working on
its synthetic data). The path and file contents are never logged.

The dataset is cached per (path, mtime, size) and loaded once under a lock;
like the in-memory imports (D6) it assumes a single worker process.
"""

from __future__ import annotations

import logging
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.connectors.pieces_file import read_pieces
from app.connectors.pin_spec import read_pin_spec
from app.core.config import get_settings
from app.engines.quality_analytics.analytics import Granularity, QualityFilter, overview
from app.engines.quality_analytics.dataset import DimensionalDataset, check_pin_pairs

logger = logging.getLogger(__name__)

REAL_DATASET_ID = "real-dimensional"
_MB = 1024 * 1024

_lock = threading.Lock()
_cache: tuple[tuple[object, ...], DimensionalDataset] | None = None
# Overview over 10^5 pieces costs seconds in pure Python; the UI re-asks the
# same few filter combinations, so keep the last results (keyed by dataset object).
_OVERVIEW_CACHE_SIZE = 32
_overview_lock = threading.Lock()
_overview_cache: OrderedDict[tuple[int, QualityFilter, str], dict[str, Any]] = OrderedDict()


def real_dataset_configured() -> bool:
    settings = get_settings()
    return bool(settings.demo_real_dataset_path) and settings.app_env != "production"


def load_real_dataset() -> DimensionalDataset | None:
    """The REAL dataset, or None when it is not configured or cannot be used."""
    global _cache
    settings = get_settings()
    path_value = settings.demo_real_dataset_path
    if not path_value:
        return None
    if settings.app_env == "production":
        logger.warning("A real dataset path is configured in production; it is ignored (plan decision D8).")
        return None
    path = Path(path_value)
    try:
        stat = path.stat()
        key = (str(path), stat.st_mtime_ns, stat.st_size, _spec_key(settings.demo_real_spec_path))
        with _lock:
            if _cache is not None and _cache[0] == key:
                return _cache[1]
            label = settings.demo_client_label
            dataset = read_pieces(
                path,
                dataset_id=REAL_DATASET_ID,
                name=f"Datos reales · {label}",
                description=(
                    f"Período cerrado del cliente ({label}), convertido fuera de línea y cargado localmente. "
                    "Veredictos OK/NOK reportados por la máquina; sin tolerancias en la fuente."
                ),
                max_bytes=settings.demo_real_dataset_max_mb * _MB,
                max_pieces=settings.demo_real_dataset_max_pieces,
            )
            _attach_pin_spec(dataset, settings.demo_real_spec_path)
            _cache = (key, dataset)
            return dataset
    except (OSError, ValueError, ValidationError):
        logger.warning("The real dataset could not be loaded; it will not be offered.")
        return None


def _spec_key(path_value: str | None) -> tuple[str, int, int] | None:
    """Part of the cache key, so editing the private spec reloads the dataset."""
    if not path_value:
        return None
    try:
        stat = Path(path_value).stat()
    except OSError:
        return None
    return (path_value, stat.st_mtime_ns, stat.st_size)


def _attach_pin_spec(dataset: DimensionalDataset, path_value: str | None) -> None:
    """IQ-F19: X/Y pairs from the private spec; an unusable spec only hides the X/Y view."""
    if not path_value:
        return
    try:
        pairs = read_pin_spec(Path(path_value))
        check_pin_pairs(pairs, dataset.values)
    except (OSError, ValueError, ValidationError):
        logger.warning("The position spec could not be loaded; the X/Y view will not be offered.")
        return
    dataset.pin_pairs = pairs


def cached_overview(ds: DimensionalDataset, f: QualityFilter, granularity: Granularity) -> dict[str, Any]:
    """`overview` with a small LRU; the key includes the dataset object, so a reload invalidates it."""
    key = (id(ds), f, granularity)
    with _overview_lock:
        hit = _overview_cache.get(key)
        if hit is not None:
            _overview_cache.move_to_end(key)
            return hit
    result = overview(ds, f, granularity)
    with _overview_lock:
        _overview_cache[key] = result
        while len(_overview_cache) > _OVERVIEW_CACHE_SIZE:
            _overview_cache.popitem(last=False)
    return result


def warm_up_in_background() -> None:
    """Load once at startup so the first request does not pay the parsing cost."""
    if real_dataset_configured():
        threading.Thread(target=load_real_dataset, name="real-dataset-warmup", daemon=True).start()


def reset_cache() -> None:
    """Tests only."""
    global _cache
    with _lock:
        _cache = None
    with _overview_lock:
        _overview_cache.clear()
