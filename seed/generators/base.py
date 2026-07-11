from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
from numpy.random import Generator
from sqlalchemy.orm import Session

from seed.config import SeedConfig


def make_rng(seed: int) -> Generator:
    """Single seeded RNG source for the whole seed run — every generator must
    derive its randomness from this (or a `.spawn()` of it), never its own
    unseeded source, or two runs with the same seed won't produce identical
    data (F3.1 acceptance criterion)."""
    return np.random.default_rng(seed)


@dataclass
class SeedContext:
    """Shared state passed to every registered generator, in registration
    order. `artifacts` is how a generator hands its output to the next one
    (e.g. F3.2's catalog generator stashes the created characteristics under
    "characteristics" for F3.3's measurement-series generator to read) —
    generators don't return values, since __main__.py just calls each in turn."""

    session: Session
    rng: Generator
    config: SeedConfig
    artifacts: dict[str, Any] = field(default_factory=dict)


GeneratorFn = Callable[[SeedContext], None]

_REGISTRY: list[GeneratorFn] = []


def register_generator(func: GeneratorFn) -> GeneratorFn:
    """Decorator F3.2-F3.4 use to plug their dataset generators into the CLI
    run order. F3.1 ships with an empty registry — no generator here yet."""
    _REGISTRY.append(func)
    return func


def registered_generators() -> list[GeneratorFn]:
    return list(_REGISTRY)
