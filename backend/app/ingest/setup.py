"""Create or reuse the master data a line ingest needs: plant hierarchy,
one machine and operation per station, the product, its recipes, one
measurement program per station and the characteristics of every measure.

Idempotent: rerunning finds existing rows by their natural keys.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingest.config import IngestConfig, StationConfig
from app.models import (
    Area,
    Base,
    Cell,
    Characteristic,
    CharacteristicClassification,
    Connector,
    DataSource,
    Line,
    Machine,
    MeasurementProgram,
    Operation,
    Organization,
    PartNumber,
    ProductFamily,
    Recipe,
    Site,
)

CLASSIFICATION_CODE = "standard"
DATA_SOURCE_TYPE = "station_export"
CONNECTOR_NAME = "station_csv_export"


@dataclass(frozen=True)
class StationIds:
    operation_id: uuid.UUID
    machine_id: uuid.UUID
    program_id: uuid.UUID


@dataclass
class LineCatalog:
    """Ids of the master data the loader writes against."""

    line_id: uuid.UUID
    part_number_id: uuid.UUID
    classification_id: uuid.UUID
    data_source_id: uuid.UUID
    connector_id: uuid.UUID
    stations: dict[str, StationIds]
    recipes: dict[int, uuid.UUID]
    # (station code, measure) -> characteristic id
    characteristics: dict[tuple[str, str], uuid.UUID] = field(default_factory=dict)


def static_measures(station: StationConfig, pins: int) -> list[str]:
    """Measures a station always reports (electrical ones are discovered)."""
    if station.kind == "pin_length":
        return ["REF"] + [f"P{n}" for n in range(1, pins + 1)]
    if station.kind == "pin_position" and station.side == "connector":
        return [f"P{n}{axis}" for n in range(1, pins + 1) for axis in ("X", "Y")]
    if station.kind == "pin_position":
        return [f"P{n}" for n in range(1, pins + 1)]
    return []


def characteristic_label(station: StationConfig, measure: str) -> tuple[str, str, str]:
    """(name, characteristic_type, unit) for a station measure."""
    if station.kind == "electrical":
        second = measure.endswith("-V2")
        mess_type, from_point, to_point = measure.removesuffix("-V2")[1:].split("-")
        suffix = " (value 2)" if second else ""
        return f"Points {from_point}-{to_point}, test type {mess_type}{suffix}", "electrical", "raw"
    if measure == "REF":
        return "Reference", "length", "mm"
    pin = measure[1:].rstrip("XY")
    if station.kind == "pin_length":
        return f"Pin {pin} length", "length", "mm"
    if measure.endswith(("X", "Y")):
        return f"Pin {pin} {measure[-1]} deviation", "position", "mm"
    return f"Pin {pin} position", "position", "mm"


ModelT = TypeVar("ModelT", bound=Base)


def _get_or_create(session: Session, model: type[ModelT], lookup: dict[str, Any], **values: Any) -> ModelT:
    stmt = select(model).filter_by(**lookup)
    found = session.execute(stmt).scalar_one_or_none()
    if found is not None:
        return found
    obj = model(**lookup, **values)
    session.add(obj)
    session.flush()
    return obj


def ensure_catalog(session: Session, config: IngestConfig, programs_valid_from: datetime) -> LineCatalog:
    """Create missing master data and return the ids. Caller commits."""
    org = _get_or_create(
        session, Organization, {"code": config.organization.code}, name=config.organization.name
    )
    site = _get_or_create(
        session,
        Site,
        {"organization_id": org.id, "code": config.site.code},
        name=config.site.name,
        timezone=config.timezone.key,
    )
    area = _get_or_create(
        session, Area, {"site_id": site.id, "code": config.area.code}, name=config.area.name
    )
    line = _get_or_create(
        session, Line, {"area_id": area.id, "code": config.line.code}, name=config.line.name
    )
    cell = _get_or_create(
        session, Cell, {"line_id": line.id, "code": config.cell.code}, name=config.cell.name
    )

    family = _get_or_create(session, ProductFamily, {"code": config.family.code}, name=config.family.name)
    part = _get_or_create(
        session,
        PartNumber,
        {"code": config.part_number.code},
        name=config.part_number.name,
        product_family_id=family.id,
    )
    classification = _get_or_create(
        session, CharacteristicClassification, {"code": CLASSIFICATION_CODE}, name="Standard"
    )
    source = _get_or_create(
        session,
        DataSource,
        {"code": f"line:{config.line.code}"},
        name=f"{config.line.name} station exports",
        source_type=DATA_SOURCE_TYPE,
    )
    connector = _get_or_create(
        session,
        Connector,
        {"data_source_id": source.id, "name": CONNECTOR_NAME},
        config={"format": "csv;latin-1"},
    )

    stations: dict[str, StationIds] = {}
    for station in config.stations:
        machine = _get_or_create(
            session,
            Machine,
            {"cell_id": cell.id, "code": station.code},
            name=station.name,
            machine_type=station.kind,
        )
        operation = _get_or_create(
            session,
            Operation,
            {"line_id": line.id, "code": station.code},
            name=station.name,
            operation_kind=station.kind,
            side=station.side,
            sequence=station.sequence,
            machine_id=machine.id,
        )
        program = session.execute(
            select(MeasurementProgram).where(
                MeasurementProgram.part_number_id == part.id,
                MeasurementProgram.name == f"{station.code} export",
                MeasurementProgram.valid_to.is_(None),
            )
        ).scalar_one_or_none()
        if program is None:
            program = MeasurementProgram(
                part_number_id=part.id,
                name=f"{station.code} export",
                version=1,
                output_mapping={"station": station.code, "kind": station.kind, "side": station.side},
                valid_from=programs_valid_from,
            )
            session.add(program)
            session.flush()
        stations[station.code] = StationIds(operation.id, machine.id, program.id)

    recipes: dict[int, uuid.UUID] = {}
    for code in sorted(config.recipes_in_scope):
        recipe = _get_or_create(
            session,
            Recipe,
            {"line_id": line.id, "code": code},
            part_number_id=part.id,
        )
        recipes[code] = recipe.id

    catalog = LineCatalog(
        line_id=line.id,
        part_number_id=part.id,
        classification_id=classification.id,
        data_source_id=source.id,
        connector_id=connector.id,
        stations=stations,
        recipes=recipes,
    )
    for station in config.stations:
        for measure in static_measures(station, config.pins):
            ensure_characteristic(session, catalog, station, measure)
    existing = session.execute(
        select(Characteristic.balloon_number, Characteristic.id).where(
            Characteristic.part_number_id == catalog.part_number_id
        )
    ).all()
    by_balloon = {balloon: char_id for balloon, char_id in existing}
    for station in config.stations:
        prefix = f"{station.code}-"
        for balloon, char_id in by_balloon.items():
            if balloon.startswith(prefix):
                catalog.characteristics[(station.code, balloon[len(prefix) :])] = char_id
    return catalog


def ensure_characteristic(
    session: Session, catalog: LineCatalog, station: StationConfig, measure: str
) -> uuid.UUID:
    key = (station.code, measure)
    if key in catalog.characteristics:
        return catalog.characteristics[key]
    name, characteristic_type, unit = characteristic_label(station, measure)
    characteristic = _get_or_create(
        session,
        Characteristic,
        {"part_number_id": catalog.part_number_id, "balloon_number": f"{station.code}-{measure}"},
        name=f"{station.name} · {name}",
        characteristic_type=characteristic_type,
        unit=unit,
        classification_id=catalog.classification_id,
    )
    catalog.characteristics[key] = characteristic.id
    return characteristic.id
