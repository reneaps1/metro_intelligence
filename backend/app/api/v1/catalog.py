"""F4.4 (MI-24): catalog CRUD API — product families, part numbers,
characteristics with versioned specifications, measurement programs,
inspection plans and versioned frequencies.

Versioning rule (CLAUDE.md §6, migration 0002_catalog.py): Specification,
MeasurementProgram, and InspectionFrequency are never updated in place.
Creating a new version closes the current active row (``valid_to = now()``)
and inserts a new one inside the same transaction, so the partial unique
index on ``valid_to IS NULL`` is never violated and history stays intact.
Every write is audited via ``app.services.audit_service`` with the model's
DB-column state before/after (never derived from client-controlled fields
directly, so the audit trail reflects what was actually persisted).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.catalog import (
    Characteristic,
    CharacteristicClassification,
    InspectionFrequency,
    InspectionPlan,
    MeasurementProgram,
    PartNumber,
    ProductFamily,
    Specification,
)
from app.models.security import User
from app.schemas.catalog import (
    CharacteristicClassificationCreate,
    CharacteristicClassificationRead,
    CharacteristicClassificationUpdate,
    CharacteristicCreate,
    CharacteristicRead,
    CharacteristicUpdate,
    InspectionFrequencyCreate,
    InspectionFrequencyRead,
    InspectionPlanCreate,
    InspectionPlanRead,
    InspectionPlanUpdate,
    MeasurementProgramCreate,
    MeasurementProgramRead,
    Page,
    PartNumberCreate,
    PartNumberRead,
    PartNumberUpdate,
    ProductFamilyCreate,
    ProductFamilyRead,
    ProductFamilyUpdate,
    SpecificationCreate,
    SpecificationRead,
)
from app.services.audit_service import AuditContext, get_audit_context, record_change, record_event

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _model_state(instance: Any, fields: list[str]) -> dict[str, Any]:
    return {field: getattr(instance, field) for field in fields}


def _paginate[ModelT](
    db: Session, stmt: Select[tuple[ModelT]], page: int, page_size: int
) -> tuple[list[ModelT], int]:
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.limit(page_size).offset((page - 1) * page_size)).scalars().all()
    return list(rows), total


def _get_or_404[ModelT](db: Session, model: type[ModelT], entity_id: uuid.UUID, label: str) -> ModelT:
    instance = db.get(model, entity_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found.")
    return instance


def _conflict_on_integrity_error(exc: IntegrityError, detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


# --- ProductFamily -----------------------------------------------------------

_FAMILY_FIELDS = ["code", "name", "description"]


@router.get("/product-families", response_model=Page[ProductFamilyRead])
def list_product_families(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    code: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.product_family", "read")),
) -> Page[ProductFamilyRead]:
    stmt = select(ProductFamily).order_by(ProductFamily.code)
    if code:
        stmt = stmt.where(ProductFamily.code.ilike(f"%{code}%"))
    items, total = _paginate(db, stmt, page, page_size)
    return Page(
        items=[ProductFamilyRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/product-families",
    response_model=ProductFamilyRead,
    status_code=status.HTTP_201_CREATED,
)
def create_product_family(
    payload: ProductFamilyCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.product_family", "create")),
    context: AuditContext = Depends(get_audit_context),
) -> ProductFamily:
    family = ProductFamily(**payload.model_dump())
    db.add(family)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise _conflict_on_integrity_error(exc, "A product family with this code already exists.") from exc
    record_event(
        db,
        context,
        action="create",
        entity_type="catalog.product_family",
        entity_id=family.id,
        after=_model_state(family, _FAMILY_FIELDS),
    )
    db.commit()
    db.refresh(family)
    return family


@router.get("/product-families/{family_id}", response_model=ProductFamilyRead)
def get_product_family(
    family_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.product_family", "read")),
) -> ProductFamily:
    return _get_or_404(db, ProductFamily, family_id, "Product family")


@router.patch("/product-families/{family_id}", response_model=ProductFamilyRead)
def update_product_family(
    family_id: uuid.UUID,
    payload: ProductFamilyUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.product_family", "update")),
    context: AuditContext = Depends(get_audit_context),
) -> ProductFamily:
    family = _get_or_404(db, ProductFamily, family_id, "Product family")
    before = _model_state(family, _FAMILY_FIELDS)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(family, key, value)
    db.flush()
    record_change(
        db,
        context,
        action="update",
        entity_type="catalog.product_family",
        entity_id=family.id,
        before=before,
        after=_model_state(family, _FAMILY_FIELDS),
    )
    db.commit()
    db.refresh(family)
    return family


# --- PartNumber ---------------------------------------------------------------

_PART_FIELDS = ["product_family_id", "code", "name", "description"]


@router.get("/part-numbers", response_model=Page[PartNumberRead])
def list_part_numbers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    product_family_id: uuid.UUID | None = None,
    code: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.part_number", "read")),
) -> Page[PartNumberRead]:
    stmt = select(PartNumber).order_by(PartNumber.code)
    if product_family_id:
        stmt = stmt.where(PartNumber.product_family_id == product_family_id)
    if code:
        stmt = stmt.where(PartNumber.code.ilike(f"%{code}%"))
    items, total = _paginate(db, stmt, page, page_size)
    return Page(
        items=[PartNumberRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/part-numbers", response_model=PartNumberRead, status_code=status.HTTP_201_CREATED)
def create_part_number(
    payload: PartNumberCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.part_number", "create")),
    context: AuditContext = Depends(get_audit_context),
) -> PartNumber:
    _get_or_404(db, ProductFamily, payload.product_family_id, "Product family")
    part = PartNumber(**payload.model_dump())
    db.add(part)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise _conflict_on_integrity_error(exc, "A part number with this code already exists.") from exc
    record_event(
        db,
        context,
        action="create",
        entity_type="catalog.part_number",
        entity_id=part.id,
        after=_model_state(part, _PART_FIELDS),
    )
    db.commit()
    db.refresh(part)
    return part


@router.get("/part-numbers/{part_id}", response_model=PartNumberRead)
def get_part_number(
    part_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.part_number", "read")),
) -> PartNumber:
    return _get_or_404(db, PartNumber, part_id, "Part number")


@router.patch("/part-numbers/{part_id}", response_model=PartNumberRead)
def update_part_number(
    part_id: uuid.UUID,
    payload: PartNumberUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.part_number", "update")),
    context: AuditContext = Depends(get_audit_context),
) -> PartNumber:
    part = _get_or_404(db, PartNumber, part_id, "Part number")
    before = _model_state(part, _PART_FIELDS)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(part, key, value)
    db.flush()
    record_change(
        db,
        context,
        action="update",
        entity_type="catalog.part_number",
        entity_id=part.id,
        before=before,
        after=_model_state(part, _PART_FIELDS),
    )
    db.commit()
    db.refresh(part)
    return part


# --- CharacteristicClassification ---------------------------------------------

_CLASSIFICATION_FIELDS = ["code", "name", "description"]


@router.get(
    "/characteristic-classifications",
    response_model=Page[CharacteristicClassificationRead],
)
def list_classifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.characteristic_classification", "read")),
) -> Page[CharacteristicClassificationRead]:
    stmt = select(CharacteristicClassification).order_by(CharacteristicClassification.code)
    items, total = _paginate(db, stmt, page, page_size)
    return Page(
        items=[CharacteristicClassificationRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/characteristic-classifications",
    response_model=CharacteristicClassificationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_classification(
    payload: CharacteristicClassificationCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.characteristic_classification", "create")),
    context: AuditContext = Depends(get_audit_context),
) -> CharacteristicClassification:
    classification = CharacteristicClassification(**payload.model_dump())
    db.add(classification)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise _conflict_on_integrity_error(exc, "A classification with this code already exists.") from exc
    record_event(
        db,
        context,
        action="create",
        entity_type="catalog.characteristic_classification",
        entity_id=classification.id,
        after=_model_state(classification, _CLASSIFICATION_FIELDS),
    )
    db.commit()
    db.refresh(classification)
    return classification


@router.patch(
    "/characteristic-classifications/{classification_id}",
    response_model=CharacteristicClassificationRead,
)
def update_classification(
    classification_id: uuid.UUID,
    payload: CharacteristicClassificationUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.characteristic_classification", "update")),
    context: AuditContext = Depends(get_audit_context),
) -> CharacteristicClassification:
    classification = _get_or_404(db, CharacteristicClassification, classification_id, "Classification")
    before = _model_state(classification, _CLASSIFICATION_FIELDS)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(classification, key, value)
    db.flush()
    record_change(
        db,
        context,
        action="update",
        entity_type="catalog.characteristic_classification",
        entity_id=classification.id,
        before=before,
        after=_model_state(classification, _CLASSIFICATION_FIELDS),
    )
    db.commit()
    db.refresh(classification)
    return classification


# --- Characteristic + Specification (versioned) -------------------------------

_CHARACTERISTIC_FIELDS = [
    "part_number_id",
    "balloon_number",
    "name",
    "characteristic_type",
    "unit",
    "classification_id",
]
_SPECIFICATION_FIELDS = ["nominal", "lower_tol", "upper_tol", "unit", "valid_from", "valid_to"]


def _active_specification(db: Session, characteristic_id: uuid.UUID) -> Specification | None:
    stmt = select(Specification).where(
        Specification.characteristic_id == characteristic_id,
        Specification.valid_to.is_(None),
    )
    return db.execute(stmt).scalar_one_or_none()


def _characteristic_read(db: Session, characteristic: Characteristic) -> CharacteristicRead:
    active_spec = _active_specification(db, characteristic.id)
    fields = ["id", *_CHARACTERISTIC_FIELDS, "created_at", "updated_at"]
    return CharacteristicRead.model_validate(
        {
            **{field: getattr(characteristic, field) for field in fields},
            "active_specification": (
                SpecificationRead.model_validate(active_spec) if active_spec is not None else None
            ),
        }
    )


@router.get("/characteristics", response_model=Page[CharacteristicRead])
def list_characteristics(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    part_number_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.characteristic", "read")),
) -> Page[CharacteristicRead]:
    stmt = select(Characteristic).order_by(Characteristic.balloon_number)
    if part_number_id:
        stmt = stmt.where(Characteristic.part_number_id == part_number_id)
    items, total = _paginate(db, stmt, page, page_size)
    return Page(
        items=[_characteristic_read(db, item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/characteristics", response_model=CharacteristicRead, status_code=status.HTTP_201_CREATED)
def create_characteristic(
    payload: CharacteristicCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.characteristic", "create")),
    context: AuditContext = Depends(get_audit_context),
) -> CharacteristicRead:
    _get_or_404(db, PartNumber, payload.part_number_id, "Part number")
    _get_or_404(db, CharacteristicClassification, payload.classification_id, "Classification")

    characteristic = Characteristic(
        part_number_id=payload.part_number_id,
        balloon_number=payload.balloon_number,
        name=payload.name,
        characteristic_type=payload.characteristic_type,
        unit=payload.unit,
        classification_id=payload.classification_id,
    )
    db.add(characteristic)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise _conflict_on_integrity_error(
            exc, "A characteristic with this balloon number already exists for this part."
        ) from exc

    spec = Specification(characteristic_id=characteristic.id, **payload.specification.model_dump())
    db.add(spec)
    db.flush()

    record_event(
        db,
        context,
        action="create",
        entity_type="catalog.characteristic",
        entity_id=characteristic.id,
        after=_model_state(characteristic, _CHARACTERISTIC_FIELDS),
    )
    record_event(
        db,
        context,
        action="create",
        entity_type="catalog.specification",
        entity_id=spec.id,
        after=_model_state(spec, _SPECIFICATION_FIELDS),
    )
    db.commit()
    db.refresh(characteristic)
    return _characteristic_read(db, characteristic)


@router.get("/characteristics/{characteristic_id}", response_model=CharacteristicRead)
def get_characteristic(
    characteristic_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.characteristic", "read")),
) -> CharacteristicRead:
    characteristic = _get_or_404(db, Characteristic, characteristic_id, "Characteristic")
    return _characteristic_read(db, characteristic)


@router.patch("/characteristics/{characteristic_id}", response_model=CharacteristicRead)
def update_characteristic(
    characteristic_id: uuid.UUID,
    payload: CharacteristicUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.characteristic", "update")),
    context: AuditContext = Depends(get_audit_context),
) -> CharacteristicRead:
    characteristic = _get_or_404(db, Characteristic, characteristic_id, "Characteristic")
    if payload.classification_id is not None:
        _get_or_404(db, CharacteristicClassification, payload.classification_id, "Classification")
    before = _model_state(characteristic, _CHARACTERISTIC_FIELDS)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(characteristic, key, value)
    db.flush()
    record_change(
        db,
        context,
        action="update",
        entity_type="catalog.characteristic",
        entity_id=characteristic.id,
        before=before,
        after=_model_state(characteristic, _CHARACTERISTIC_FIELDS),
    )
    db.commit()
    db.refresh(characteristic)
    return _characteristic_read(db, characteristic)


@router.get(
    "/characteristics/{characteristic_id}/specifications",
    response_model=list[SpecificationRead],
)
def list_specifications(
    characteristic_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.specification", "read")),
) -> list[Specification]:
    _get_or_404(db, Characteristic, characteristic_id, "Characteristic")
    stmt = (
        select(Specification)
        .where(Specification.characteristic_id == characteristic_id)
        .order_by(Specification.valid_from.desc())
    )
    return list(db.execute(stmt).scalars().all())


@router.post(
    "/characteristics/{characteristic_id}/specifications",
    response_model=SpecificationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_specification_version(
    characteristic_id: uuid.UUID,
    payload: SpecificationCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.specification", "create")),
    context: AuditContext = Depends(get_audit_context),
) -> Specification:
    """Create a new spec version. Never updates an existing row: this closes
    the currently active version (if any) and inserts a fresh one, so history
    stays intact (CLAUDE.md §6) and the DB's partial unique index on
    ``valid_to IS NULL`` per characteristic is never violated."""
    _get_or_404(db, Characteristic, characteristic_id, "Characteristic")
    current = _active_specification(db, characteristic_id)

    new_spec = Specification(characteristic_id=characteristic_id, **payload.model_dump())
    db.add(new_spec)

    if current is not None:
        before = _model_state(current, _SPECIFICATION_FIELDS)
        current.valid_to = func.now()
        db.flush()
        record_change(
            db,
            context,
            action="close_version",
            entity_type="catalog.specification",
            entity_id=current.id,
            before=before,
            after=_model_state(current, _SPECIFICATION_FIELDS),
        )
    else:
        db.flush()

    record_event(
        db,
        context,
        action="create_version",
        entity_type="catalog.specification",
        entity_id=new_spec.id,
        after=_model_state(new_spec, _SPECIFICATION_FIELDS),
    )
    db.commit()
    db.refresh(new_spec)
    return new_spec


# --- MeasurementProgram (versioned) -------------------------------------------

_PROGRAM_FIELDS = ["name", "version", "output_mapping", "valid_from", "valid_to"]


def _active_program(db: Session, part_number_id: uuid.UUID, name: str) -> MeasurementProgram | None:
    stmt = select(MeasurementProgram).where(
        MeasurementProgram.part_number_id == part_number_id,
        MeasurementProgram.name == name,
        MeasurementProgram.valid_to.is_(None),
    )
    return db.execute(stmt).scalar_one_or_none()


@router.get(
    "/part-numbers/{part_id}/measurement-programs",
    response_model=list[MeasurementProgramRead],
)
def list_measurement_programs(
    part_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.measurement_program", "read")),
) -> list[MeasurementProgram]:
    _get_or_404(db, PartNumber, part_id, "Part number")
    stmt = (
        select(MeasurementProgram)
        .where(MeasurementProgram.part_number_id == part_id)
        .order_by(MeasurementProgram.name, MeasurementProgram.version.desc())
    )
    return list(db.execute(stmt).scalars().all())


@router.post(
    "/part-numbers/{part_id}/measurement-programs",
    response_model=MeasurementProgramRead,
    status_code=status.HTTP_201_CREATED,
)
def create_measurement_program_version(
    part_id: uuid.UUID,
    payload: MeasurementProgramCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.measurement_program", "create")),
    context: AuditContext = Depends(get_audit_context),
) -> MeasurementProgram:
    _get_or_404(db, PartNumber, part_id, "Part number")
    current = _active_program(db, part_id, payload.name)
    next_version = current.version + 1 if current is not None else 1

    new_program = MeasurementProgram(
        part_number_id=part_id,
        name=payload.name,
        version=next_version,
        output_mapping=payload.output_mapping,
    )
    db.add(new_program)

    if current is not None:
        before = _model_state(current, _PROGRAM_FIELDS)
        current.valid_to = func.now()
        db.flush()
        record_change(
            db,
            context,
            action="close_version",
            entity_type="catalog.measurement_program",
            entity_id=current.id,
            before=before,
            after=_model_state(current, _PROGRAM_FIELDS),
        )
    else:
        db.flush()

    record_event(
        db,
        context,
        action="create_version",
        entity_type="catalog.measurement_program",
        entity_id=new_program.id,
        after=_model_state(new_program, _PROGRAM_FIELDS),
    )
    db.commit()
    db.refresh(new_program)
    return new_program


# --- InspectionPlan + InspectionFrequency (versioned) -------------------------

_PLAN_FIELDS = ["part_number_id", "name", "description", "is_active"]
_FREQUENCY_FIELDS = [
    "inspection_plan_id",
    "characteristic_id",
    "frequency_type",
    "frequency_value",
    "reason",
    "changed_by_user_id",
    "decision_id",
    "valid_from",
    "valid_to",
]


@router.get("/inspection-plans", response_model=Page[InspectionPlanRead])
def list_inspection_plans(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    part_number_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.inspection_plan", "read")),
) -> Page[InspectionPlanRead]:
    stmt = select(InspectionPlan).order_by(InspectionPlan.name)
    if part_number_id:
        stmt = stmt.where(InspectionPlan.part_number_id == part_number_id)
    items, total = _paginate(db, stmt, page, page_size)
    return Page(
        items=[InspectionPlanRead.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/inspection-plans", response_model=InspectionPlanRead, status_code=status.HTTP_201_CREATED)
def create_inspection_plan(
    payload: InspectionPlanCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.inspection_plan", "create")),
    context: AuditContext = Depends(get_audit_context),
) -> InspectionPlan:
    _get_or_404(db, PartNumber, payload.part_number_id, "Part number")
    plan = InspectionPlan(**payload.model_dump())
    db.add(plan)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise _conflict_on_integrity_error(
            exc, "An inspection plan with this name already exists for this part."
        ) from exc
    record_event(
        db,
        context,
        action="create",
        entity_type="catalog.inspection_plan",
        entity_id=plan.id,
        after=_model_state(plan, _PLAN_FIELDS),
    )
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/inspection-plans/{plan_id}", response_model=InspectionPlanRead)
def get_inspection_plan(
    plan_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.inspection_plan", "read")),
) -> InspectionPlan:
    return _get_or_404(db, InspectionPlan, plan_id, "Inspection plan")


@router.patch("/inspection-plans/{plan_id}", response_model=InspectionPlanRead)
def update_inspection_plan(
    plan_id: uuid.UUID,
    payload: InspectionPlanUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.inspection_plan", "update")),
    context: AuditContext = Depends(get_audit_context),
) -> InspectionPlan:
    plan = _get_or_404(db, InspectionPlan, plan_id, "Inspection plan")
    before = _model_state(plan, _PLAN_FIELDS)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, key, value)
    db.flush()
    record_change(
        db,
        context,
        action="update",
        entity_type="catalog.inspection_plan",
        entity_id=plan.id,
        before=before,
        after=_model_state(plan, _PLAN_FIELDS),
    )
    db.commit()
    db.refresh(plan)
    return plan


def _active_frequency(
    db: Session, plan_id: uuid.UUID, characteristic_id: uuid.UUID
) -> InspectionFrequency | None:
    stmt = select(InspectionFrequency).where(
        InspectionFrequency.inspection_plan_id == plan_id,
        InspectionFrequency.characteristic_id == characteristic_id,
        InspectionFrequency.valid_to.is_(None),
    )
    return db.execute(stmt).scalar_one_or_none()


@router.get(
    "/inspection-plans/{plan_id}/frequencies",
    response_model=list[InspectionFrequencyRead],
)
def list_inspection_frequencies(
    plan_id: uuid.UUID,
    characteristic_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.inspection_frequency", "read")),
) -> list[InspectionFrequency]:
    _get_or_404(db, InspectionPlan, plan_id, "Inspection plan")
    stmt = (
        select(InspectionFrequency)
        .where(InspectionFrequency.inspection_plan_id == plan_id)
        .order_by(InspectionFrequency.valid_from.desc())
    )
    if characteristic_id:
        stmt = stmt.where(InspectionFrequency.characteristic_id == characteristic_id)
    return list(db.execute(stmt).scalars().all())


@router.post(
    "/inspection-plans/{plan_id}/frequencies",
    response_model=InspectionFrequencyRead,
    status_code=status.HTTP_201_CREATED,
)
def create_inspection_frequency_version(
    plan_id: uuid.UUID,
    payload: InspectionFrequencyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("catalog.inspection_frequency", "create")),
    context: AuditContext = Depends(get_audit_context),
) -> InspectionFrequency:
    """Create a new frequency version for one characteristic within a plan.

    This is a recommendation-support record, not an automatic production
    action (CLAUDE.md §2): the caller is an authorized human (quality_engineer
    or admin per docs/security/rbac.md), never the adaptive inspection engine
    writing directly. ``decision_id`` links to a prior human decision when
    this change followed an accepted recommendation (F10.D)."""
    _get_or_404(db, InspectionPlan, plan_id, "Inspection plan")
    _get_or_404(db, Characteristic, payload.characteristic_id, "Characteristic")
    current = _active_frequency(db, plan_id, payload.characteristic_id)

    new_frequency = InspectionFrequency(
        inspection_plan_id=plan_id,
        characteristic_id=payload.characteristic_id,
        frequency_type=payload.frequency_type,
        frequency_value=payload.frequency_value,
        reason=payload.reason,
        changed_by_user_id=current_user.id,
    )
    db.add(new_frequency)

    if current is not None:
        before = _model_state(current, _FREQUENCY_FIELDS)
        current.valid_to = func.now()
        db.flush()
        record_change(
            db,
            context,
            action="close_version",
            entity_type="catalog.inspection_frequency",
            entity_id=current.id,
            before=before,
            after=_model_state(current, _FREQUENCY_FIELDS),
        )
    else:
        db.flush()

    record_event(
        db,
        context,
        action="create_version",
        entity_type="catalog.inspection_frequency",
        entity_id=new_frequency.id,
        after=_model_state(new_frequency, _FREQUENCY_FIELDS),
    )
    db.commit()
    db.refresh(new_frequency)
    return new_frequency
