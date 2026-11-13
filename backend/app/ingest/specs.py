"""Import versioned specifications for a line's characteristics.

The specification file (outside the repo, ADR-004) names a station and a
measure family; see `specs.example.yaml`. A new version closes the active
one at its `valid_from`; results are never updated: compliance against the
new version is reflected when the daily statistics are rebuilt (ADR-005).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingest.config import ConfigError, IngestConfig
from app.ingest.setup import LineCatalog
from app.models import Characteristic, Specification
from app.services.audit_service import write_audit_log

AUDIT_ACTION = "specifications_imported"
AUDIT_ACTOR = "cli:import_specifications"
MEASURES = ("pin", "pin_x", "pin_y", "ref")


@dataclass(frozen=True)
class SpecEntry:
    station: str
    measure: str
    nominal: Decimal
    lower_tol: Decimal | None
    upper_tol: Decimal | None
    pins: tuple[int, ...] | None


@dataclass(frozen=True)
class SpecFile:
    source: str
    valid_from: datetime
    entries: tuple[SpecEntry, ...]


def _decimal(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def parse_spec_file(raw: dict[str, Any]) -> SpecFile:
    try:
        valid_from = datetime.fromisoformat(str(raw["valid_from"]).replace("Z", "+00:00"))
        source = str(raw["source"])
        nodes = raw["specifications"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigError(f"Specification file needs source, valid_from and specifications: {exc}") from exc
    if valid_from.tzinfo is None:
        raise ConfigError("valid_from must include a timezone (e.g. 2025-01-01T00:00:00Z).")
    entries = []
    for index, node in enumerate(nodes):
        measure = str(node.get("measure", ""))
        if measure not in MEASURES:
            raise ConfigError(f"specifications[{index}].measure must be one of {', '.join(MEASURES)}.")
        entry = SpecEntry(
            station=str(node["station"]),
            measure=measure,
            nominal=Decimal(str(node["nominal"])),
            lower_tol=_decimal(node.get("lower_tol")),
            upper_tol=_decimal(node.get("upper_tol")),
            pins=tuple(int(p) for p in node["pins"]) if node.get("pins") else None,
        )
        if entry.lower_tol is None and entry.upper_tol is None:
            raise ConfigError(f"specifications[{index}] needs lower_tol, upper_tol or both.")
        entries.append(entry)
    return SpecFile(source=source, valid_from=valid_from, entries=tuple(entries))


def load_spec_file(path: Path) -> SpecFile:
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} does not contain a YAML mapping.")
    return parse_spec_file(raw)


def _measures_for(config: IngestConfig, entry: SpecEntry) -> list[str]:
    station = config.station(entry.station)
    pins = entry.pins or tuple(range(1, config.pins + 1))
    if entry.measure == "ref":
        if station.kind != "pin_length":
            raise ConfigError(f"Station {station.code} has no reference measurement.")
        return ["REF"]
    if entry.measure in ("pin_x", "pin_y"):
        if not station.is_connector_position:
            raise ConfigError(
                f"pin_x/pin_y apply only to connector pin_position stations, not {station.code}."
            )
        axis = "X" if entry.measure == "pin_x" else "Y"
        return [f"P{n}{axis}" for n in pins]
    if station.kind == "pin_length" or (station.kind == "pin_position" and station.side == "pcb"):
        return [f"P{n}" for n in pins]
    raise ConfigError(f"measure 'pin' does not apply to station {station.code}.")


def import_specifications(
    session: Session, config: IngestConfig, catalog: LineCatalog, spec_file: SpecFile
) -> list[uuid.UUID]:
    """Create the new versions and close the active ones. Caller commits."""
    created: list[uuid.UUID] = []
    summary: list[dict[str, Any]] = []
    for entry in spec_file.entries:
        for measure in _measures_for(config, entry):
            characteristic_id = catalog.characteristics.get((entry.station, measure))
            if characteristic_id is None:
                raise ConfigError(f"No characteristic for {entry.station} {measure}; run ingest setup first.")
            characteristic = session.get(Characteristic, characteristic_id)
            assert characteristic is not None
            active = session.execute(
                select(Specification).where(
                    Specification.characteristic_id == characteristic_id, Specification.valid_to.is_(None)
                )
            ).scalar_one_or_none()
            if active is not None:
                same = (active.nominal, active.lower_tol, active.upper_tol) == (
                    entry.nominal,
                    entry.lower_tol,
                    entry.upper_tol,
                )
                if same:
                    continue
                if active.valid_from >= spec_file.valid_from:
                    raise ConfigError(
                        f"{characteristic.balloon_number}: valid_from must be after the active version's "
                        f"({active.valid_from.isoformat()})."
                    )
                active.valid_to = spec_file.valid_from
            spec = Specification(
                characteristic_id=characteristic_id,
                nominal=entry.nominal,
                lower_tol=entry.lower_tol,
                upper_tol=entry.upper_tol,
                unit=characteristic.unit,
                valid_from=spec_file.valid_from,
            )
            session.add(spec)
            session.flush()
            created.append(spec.id)
            summary.append(
                {
                    "characteristic": characteristic.balloon_number,
                    "nominal": str(entry.nominal),
                    "lower_tol": None if entry.lower_tol is None else str(entry.lower_tol),
                    "upper_tol": None if entry.upper_tol is None else str(entry.upper_tol),
                }
            )
    if created:
        write_audit_log(
            session,
            action=AUDIT_ACTION,
            entity_type="specification",
            actor_identifier=AUDIT_ACTOR,
            after_state={
                "source": spec_file.source,
                "valid_from": spec_file.valid_from.isoformat(),
                "specifications": summary,
            },
        )
    return created
