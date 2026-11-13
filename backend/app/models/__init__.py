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
from app.models.context import ProcessEvent
from app.models.intelligence import (
    ActionTaken,
    Alert,
    Decision,
    Recommendation,
    RiskAssessment,
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
from app.models.process import (
    CharacteristicDaily,
    Operation,
    PartInstance,
    Recipe,
    StatsBuild,
    StepDaily,
    StepResult,
)
from app.models.security import (
    AuditLog,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)

__all__ = [
    "ActionTaken",
    "Alert",
    "Area",
    "AuditLog",
    "Base",
    "Cell",
    "CharacteristicDaily",
    "Characteristic",
    "CharacteristicClassification",
    "Connector",
    "DataSource",
    "Decision",
    "ImportedFile",
    "InspectionFrequency",
    "InspectionPlan",
    "Line",
    "Machine",
    "MeasurementProgram",
    "MeasurementResult",
    "MeasurementRun",
    "MeasurementSample",
    "Operation",
    "Organization",
    "PartInstance",
    "PartNumber",
    "Permission",
    "ProcessEvent",
    "ProductFamily",
    "Recipe",
    "Recommendation",
    "RiskAssessment",
    "Role",
    "RolePermission",
    "Site",
    "StatsBuild",
    "StepDaily",
    "StepResult",
    "Specification",
    "User",
    "UserRole",
]
