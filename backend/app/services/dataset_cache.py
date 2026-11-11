"""IQ-F21: one place to drop every derived cache of a dataset when it is unloaded or reloaded.

Several services cache results computed from a loaded `DimensionalDataset`
(overview, line panel, predictive studies, process join). With more than one
private dataset loaded lazily and evicted by an LRU, a cache keyed only by
``id(dataset)`` could hand one dataset's result to another (CPython reuses
object ids), and a cache holding the dataset object would keep evicted data in
memory. Each cache registers a ``forget(dataset_id)`` here; the registry calls
`forget` whenever it evicts or reloads a dataset.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

_lock = threading.Lock()
_forgetters: list[Callable[[str], None]] = []


def register(forget: Callable[[str], None]) -> None:
    with _lock:
        if forget not in _forgetters:
            _forgetters.append(forget)


def forget(dataset_id: str) -> None:
    with _lock:
        callbacks = list(_forgetters)
    for callback in callbacks:
        callback(dataset_id)
