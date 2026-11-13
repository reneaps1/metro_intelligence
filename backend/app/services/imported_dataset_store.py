"""IQ-F6: in-memory store for dimensional datasets built from uploaded CSVs.

Decision D6 (docs/tasks/IQ-plan-demo-industrial-quality.md): an imported
dimensional CSV is an *exploratory analysis*, not an ingestion into the
immutable measurement history (that remains the F4.5 `/imports` path). It
is held only in this process's memory, for its owner, with a TTL and a size
cap -- nothing is written to PostgreSQL or MinIO, so a customer file never
persists on a demo server. Only an audit event (who, when, file hash,
counts) is recorded.

Limitation: per process. The backend runs a single uvicorn worker; with
several workers a dataset would only be visible in the worker that built it.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.core.config import get_settings
from app.engines.quality_analytics.dataset import DimensionalDataset

IMPORTED_PREFIX = "import-"
MAX_DATASETS_PER_USER = 3
MAX_DATASETS_TOTAL = 12


@dataclass
class StoredDataset:
    dataset: DimensionalDataset
    owner_id: uuid.UUID
    created_at: float
    filename: str
    report: dict[str, Any]


class ImportedDatasetStore:
    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._items: OrderedDict[str, StoredDataset] = OrderedDict()
        self._lock = threading.Lock()

    def _purge(self, now: float) -> None:
        for key in [k for k, item in self._items.items() if now - item.created_at > self._ttl]:
            del self._items[key]

    def put(self, item: StoredDataset) -> None:
        with self._lock:
            self._purge(item.created_at)
            own = [k for k, v in self._items.items() if v.owner_id == item.owner_id]
            while len(own) >= MAX_DATASETS_PER_USER:
                del self._items[own.pop(0)]
            while len(self._items) >= MAX_DATASETS_TOTAL:
                self._items.popitem(last=False)
            self._items[item.dataset.id] = item

    def get(self, dataset_id: str, owner_id: uuid.UUID) -> StoredDataset | None:
        with self._lock:
            self._purge(time.time())
            item = self._items.get(dataset_id)
            return item if item is not None and item.owner_id == owner_id else None

    def list_for(self, owner_id: uuid.UUID) -> list[StoredDataset]:
        with self._lock:
            self._purge(time.time())
            return [v for v in reversed(self._items.values()) if v.owner_id == owner_id]

    def delete(self, dataset_id: str, owner_id: uuid.UUID) -> bool:
        with self._lock:
            item = self._items.get(dataset_id)
            if item is None or item.owner_id != owner_id:
                return False
            del self._items[dataset_id]
            return True

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


def new_dataset_id() -> str:
    return f"{IMPORTED_PREFIX}{uuid.uuid4().hex}"


@lru_cache
def get_imported_dataset_store() -> ImportedDatasetStore:
    return ImportedDatasetStore(ttl_seconds=get_settings().dimensional_import_ttl_minutes * 60)
