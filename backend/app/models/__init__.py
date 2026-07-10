"""SQLAlchemy model registry."""

from app.models.base import Base
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
from app.models.measurement import (
    Connector,
    DataSource,
    ImportedFile,
    MeasurementResult,
    MeasurementRun,
    MeasurementSample,
)
from app.models.org import Area, Cell, Line, Machine, Organization, Site
from app.models.security import (
    AuditLog,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)

__all__ = [
    "Area",
    "AuditLog",
    "Base",
    "Cell",
    "Characteristic",
    "CharacteristicClassification",
    "Connector",
    "DataSource",
    "ImportedFile",
    "InspectionFrequency",
    "InspectionPlan",
    "Line",
    "Machine",
    "MeasurementProgram",
    "MeasurementResult",
    "MeasurementRun",
    "MeasurementSample",
    "Organization",
    "PartNumber",
    "Permission",
    "ProductFamily",
    "Role",
    "RolePermission",
    "Site",
    "Specification",
    "User",
    "UserRole",
]
