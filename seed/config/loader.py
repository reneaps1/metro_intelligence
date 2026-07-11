from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCENARIOS_PATH = Path(__file__).with_name("scenarios.yaml")


@dataclass(frozen=True)
class SeedSettings:
    default_seed: int
    history_days: int
    point_interval_days: int


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    noise_std_fraction_of_tolerance: float
    drift_fraction: float = 0.0
    shift_fraction: float = 0.0
    event_day_offset: int | None = None
    nok_outlier_probability: float = 0.0
    nok_outlier_magnitude_fraction: float = 1.0


@dataclass(frozen=True)
class SeedConfig:
    settings: SeedSettings
    scenarios: dict[str, Scenario]

    def scenario(self, name: str) -> Scenario:
        try:
            return self.scenarios[name]
        except KeyError as exc:
            available = ", ".join(sorted(self.scenarios))
            raise ValueError(f"Unknown scenario '{name}'. Available: {available}") from exc


def load_config(path: Path = SCENARIOS_PATH) -> SeedConfig:
    """Parse seed/config/scenarios.yaml into typed, validated config objects."""
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))

    seed_raw = raw["seed"]
    settings = SeedSettings(
        default_seed=int(seed_raw["default_seed"]),
        history_days=int(seed_raw["history_days"]),
        point_interval_days=int(seed_raw["point_interval_days"]),
    )

    scenarios: dict[str, Scenario] = {}
    for name, fields in raw["scenarios"].items():
        scenarios[name] = Scenario(
            name=name,
            description=fields["description"],
            noise_std_fraction_of_tolerance=float(fields["noise_std_fraction_of_tolerance"]),
            drift_fraction=float(fields.get("drift_fraction", 0.0)),
            shift_fraction=float(fields.get("shift_fraction", 0.0)),
            event_day_offset=fields.get("event_day_offset"),
            nok_outlier_probability=float(fields.get("nok_outlier_probability", 0.0)),
            nok_outlier_magnitude_fraction=float(fields.get("nok_outlier_magnitude_fraction", 1.0)),
        )

    if not scenarios:
        raise ValueError(f"No scenarios declared in {path}")

    return SeedConfig(settings=settings, scenarios=scenarios)
