"""Ingest config: the line, its stations in order and the recipe scope.

Loaded from a YAML file outside the repository (ADR-004). See
`config.example.yaml` for the shape; every field is validated here so a
typo fails before any file is read.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

STATION_KINDS = ("electrical", "pin_length", "pin_position", "type_check")
STATION_SIDES = ("pcb", "connector")


class ConfigError(ValueError):
    """The ingest config is missing a field or has an invalid value."""


@dataclass(frozen=True)
class CodeName:
    code: str
    name: str


@dataclass(frozen=True)
class StationConfig:
    sequence: int
    code: str
    name: str
    kind: str
    folder: str
    file_prefix: str
    side: str | None = None
    programs: tuple[int, ...] | None = None

    @property
    def is_connector_position(self) -> bool:
        return self.kind == "pin_position" and self.side == "connector"


@dataclass(frozen=True)
class IngestConfig:
    organization: CodeName
    site: CodeName
    area: CodeName
    line: CodeName
    cell: CodeName
    timezone: ZoneInfo
    family: CodeName
    part_number: CodeName
    pins: int
    recipes_in_scope: frozenset[int]
    stations: tuple[StationConfig, ...]

    @property
    def type_check(self) -> StationConfig:
        return next(s for s in self.stations if s.kind == "type_check")

    def station(self, code: str) -> StationConfig:
        for station in self.stations:
            if station.code == code:
                return station
        raise ConfigError(f"Unknown station code {code!r}.")


def _require(mapping: dict[str, Any], key: str, where: str) -> Any:
    if not isinstance(mapping, dict) or key not in mapping or mapping[key] in (None, ""):
        raise ConfigError(f"Missing '{key}' in {where}.")
    return mapping[key]


def _code_name(mapping: dict[str, Any], key: str, where: str) -> CodeName:
    node = _require(mapping, key, where)
    return CodeName(
        code=str(_require(node, "code", f"{where}.{key}")), name=str(_require(node, "name", f"{where}.{key}"))
    )


def _station(node: dict[str, Any], index: int) -> StationConfig:
    where = f"stations[{index}]"
    kind = str(_require(node, "kind", where))
    if kind not in STATION_KINDS:
        raise ConfigError(f"{where}.kind must be one of {', '.join(STATION_KINDS)}.")
    side = node.get("side")
    if side is not None and side not in STATION_SIDES:
        raise ConfigError(f"{where}.side must be one of {', '.join(STATION_SIDES)}.")
    if kind in ("pin_length", "pin_position") and side is None:
        raise ConfigError(f"{where}.side is required for {kind} stations.")
    programs = node.get("programs")
    return StationConfig(
        sequence=int(_require(node, "sequence", where)),
        code=str(_require(node, "code", where)),
        name=str(_require(node, "name", where)),
        kind=kind,
        folder=str(_require(node, "folder", where)),
        file_prefix=str(_require(node, "file_prefix", where)),
        side=side,
        programs=tuple(int(p) for p in programs) if programs else None,
    )


def parse_config(raw: dict[str, Any]) -> IngestConfig:
    plant = _require(raw, "plant", "config")
    product = _require(raw, "product", "config")
    recipes = _require(raw, "recipes", "config")
    stations = tuple(_station(node, i) for i, node in enumerate(_require(raw, "stations", "config")))

    kinds = [s.kind for s in stations]
    if kinds.count("type_check") != 1:
        raise ConfigError("Exactly one type_check station is required: it defines each piece's recipe.")
    sequences = [s.sequence for s in stations]
    codes = [s.code for s in stations]
    if len(set(sequences)) != len(sequences) or len(set(codes)) != len(codes):
        raise ConfigError("Station sequences and codes must be unique.")

    try:
        timezone = ZoneInfo(str(_require(plant, "timezone", "plant")))
    except Exception as exc:  # ZoneInfoNotFoundError and invalid keys
        raise ConfigError(f"plant.timezone is not a valid IANA timezone: {exc}") from exc

    pins = int(_require(product, "pins", "product"))
    if pins < 1:
        raise ConfigError("product.pins must be at least 1.")

    return IngestConfig(
        organization=_code_name(plant, "organization", "plant"),
        site=_code_name(plant, "site", "plant"),
        area=_code_name(plant, "area", "plant"),
        line=_code_name(plant, "line", "plant"),
        cell=_code_name(plant, "cell", "plant"),
        timezone=timezone,
        family=_code_name(product, "family", "product"),
        part_number=_code_name(product, "part_number", "product"),
        pins=pins,
        recipes_in_scope=frozenset(int(r) for r in _require(recipes, "in_scope", "recipes")),
        stations=tuple(sorted(stations, key=lambda s: s.sequence)),
    )


def load_config(path: Path) -> IngestConfig:
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} does not contain a YAML mapping.")
    return parse_config(raw)
