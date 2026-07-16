# RBAC Matrix

This document is the access-control contract for Metro Intelligence. It is the
source of truth for backend authorization dependencies, frontend route guards,
and role x endpoint tests.

Related task: MI-4 / F0.3.

## Principles

- **Deny by default:** every endpoint, route, command, and background action is
  denied unless this document grants a specific permission.
- **Least privilege:** roles receive only the actions required for their work.
- **Human decision gate:** recommendations are suggestions only. Only
  `quality_engineer` and `admin` may accept or reject recommendations.
- **Immutable measurement history:** no role may update or delete historical
  `MeasurementResult`, `MeasurementSample`, or `MeasurementRun` records.
  Corrections create new superseding records and preserve the original.
- **Auditable state changes:** changes to master data, imports, events,
  recommendations, decisions, users, roles, permissions, and configuration must
  produce an `AuditLog` entry.
- **No automatic production action:** permissions can authorize UI/API actions
  inside the platform, but never machine release, automatic frequency changes,
  or machine/process/tooling adjustment.

## Roles

| Role | Purpose | Demo users |
|---|---|---|
| `viewer` | Read-only user for dashboards and reports. Sees summarized quality state but cannot inspect audit logs or perform operational actions. | Plant or quality leadership demo account. |
| `metrologist` | Runs the metrology workflow: imports files, reviews measurement runs, views recommendations and alerts. | Measurement room operator demo account. |
| `quality_engineer` | Owns engineering review: manages inspection plans/frequencies, evaluates risks, and accepts or rejects recommendations. | Quality engineering demo account. |
| `admin` | Administers master data, users, roles, permissions, connectors, configuration, and may act as a quality decision authority when needed. | System owner demo account. |
| `auditor` | Read-only access to the full traceability record, including audit logs. No create, update, decide, or administer permissions. | Audit/customer review demo account. |

Future enterprise mapping (F11): each role may map to one or more AD/LDAP or
IdP groups. Group names are deployment configuration, not code constants. The
application still evaluates internal role names and permission tokens.

Suggested future group mapping:

| Internal role | Example AD/LDAP group |
|---|---|
| `viewer` | `MI_Viewers` |
| `metrologist` | `MI_Metrologists` |
| `quality_engineer` | `MI_Quality_Engineers` |
| `admin` | `MI_Admins` |
| `auditor` | `MI_Auditors` |

## Actions

| Action | Meaning |
|---|---|
| `read` | View or list a resource. |
| `create` | Create a new resource or append a new history/event row. |
| `update` | Modify a mutable current-state resource. For versioned resources, this means creating a new version or closing the active version, never destructive editing. |
| `decide` | Accept/reject/supersede a recommendation or record the human decision tied to it. |
| `administer` | Manage access, configuration, connectors, retention, or system-level behavior for the resource. |

`system` in the matrix means only trusted application code may do the action as
part of an audited workflow; no human role receives that direct permission.

Role abbreviations used below:

- `V` = `viewer`
- `M` = `metrologist`
- `QE` = `quality_engineer`
- `AD` = `admin`
- `AU` = `auditor`

## Permission Matrix

| Module | Resource | read | create | update | decide | administer | Rules |
|---|---|---:|---:|---:|---:|---:|---|
| `org` | `Organization` | V, M, QE, AD, AU | AD | AD | none | AD | Demo has one organization; changes are audited. |
| `org` | `Site` | V, M, QE, AD, AU | AD | AD | none | AD | Site hierarchy is master data. |
| `org` | `Area` | V, M, QE, AD, AU | AD | AD | none | AD | Area hierarchy is master data. |
| `org` | `Line` | V, M, QE, AD, AU | AD | AD | none | AD | Used by process events and dashboards. |
| `org` | `Cell` | V, M, QE, AD, AU | AD | AD | none | AD | Post-demo depth; still protected as master data. |
| `assets` | `Machine` | V, M, QE, AD, AU | AD | AD | none | AD | Demo asset type; no command path to machines. |
| `assets` | `Process` | QE, AD, AU | AD | AD | none | AD | Referenced context only; not MES. |
| `assets` | `Operation` | QE, AD, AU | AD | AD | none | AD | Referenced context only. |
| `assets` | `Tooling` | QE, AD, AU | AD | AD | none | AD | Referenced context only; no maintenance management. |
| `assets` | `Fixture` | QE, AD, AU | AD | AD | none | AD | Referenced context only. |
| `catalog` | `ProductFamily` | V, M, QE, AD, AU | AD | AD | none | AD | Master catalog data. |
| `catalog` | `PartNumber` | V, M, QE, AD, AU | AD | AD | none | AD | Never use real customer part numbers in seed/demo. |
| `catalog` | `Characteristic` | V, M, QE, AD, AU | AD | AD | none | AD | Balloon number unique per part. |
| `catalog` | `CharacteristicClassification` | V, M, QE, AD, AU | AD | AD | none | AD | CC/SC/standard definitions affect risk. |
| `catalog` | `Specification` | V, M, QE, AD, AU | AD | AD | none | AD | Versioned tolerance records; no destructive edits. |
| `catalog` | `MeasurementProgram` | M, QE, AD, AU | AD | AD | none | AD | Versioned mappings from source output to characteristics. |
| `catalog` | `InspectionPlan` | V, M, QE, AD, AU | QE, AD | QE, AD | none | AD | Engineers manage strategy; every change audited. |
| `catalog` | `InspectionFrequency` | V, M, QE, AD, AU | QE, AD, system | QE, AD, system | none | AD | Frequency change is a history row and may link to a decision. |
| `measurement` | `MeasurementRun` | M, QE, AD, AU | M, AD, system | none | none | AD | Runs are immutable after ingestion. Corrections create new runs/versions. |
| `measurement` | `MeasurementSample` | M, QE, AD, AU | M, AD, system | none | none | AD | Samples are immutable after ingestion. |
| `measurement` | `MeasurementResult` | M, QE, AD, AU | M, AD, system | none | none | AD | Historical measurements are immutable. Superseding rows handle corrections. |
| `measurement` | `ImportedFile` | M, QE, AD, AU | M, AD, system | system | none | AD | Raw files retained; parse status can change only by import workflow. |
| `measurement` | `DataSource` | M, QE, AD, AU | AD | AD | none | AD | Source registry is connector/configuration data. |
| `measurement` | `Connector` | QE, AD, AU | AD | AD | none | AD | Connector management is admin-only; no direct engine dependency on a vendor. |
| `context` | `ProcessEvent` | M, QE, AD, AU | M, QE, AD | QE, AD | none | AD | Events explain risk; no maintenance system behavior. |
| `context` | `ProcessParameter` | QE, AD, AU | QE, AD, system | QE, AD | none | AD | Post-demo contextual data. |
| `context` | `BatchLot` | M, QE, AD, AU | M, QE, AD, system | QE, AD | none | AD | Reference only; not ERP/MES ownership. |
| `context` | `Order` | QE, AD, AU | QE, AD, system | QE, AD | none | AD | Reference only; not ERP ownership. |
| `context` | `Material` | QE, AD, AU | QE, AD, system | QE, AD | none | AD | Reference only. |
| `context` | `Shift` | M, QE, AD, AU | AD | AD | none | AD | Used for filtering and trend context. |
| `context` | `Operator` | M, QE, AD, AU | AD | AD | none | AD | Pseudonymize where possible; avoid unnecessary personal data. |
| `intelligence` | `RiskAssessment` | V, M, QE, AD, AU | system | none | none | AD | Engine output; carries version, inputs, and factors. |
| `intelligence` | `Recommendation` | M, QE, AD, AU | system | system | QE, AD | AD | Only QE/AD can accept or reject. System may supersede/expire. |
| `intelligence` | `Decision` | QE, AD, AU | QE, AD | none | QE, AD | AD | Decisions are immutable once recorded. |
| `intelligence` | `ActionTaken` | QE, AD, AU | QE, AD | QE, AD | none | AD | Records human follow-up and outcome; no machine automation. |
| `intelligence` | `Alert` | V, M, QE, AD, AU | system | V, M, QE, AD | none | AD | Users may mark read/acknowledged; trigger/severity is system/admin controlled. |
| `security` | `User` | AD, AU | AD | AD | none | AD | Admin manages local demo users; enterprise IdP mapping comes later. |
| `security` | `Role` | AD, AU | AD | AD | none | AD | Role changes are audited. |
| `security` | `Permission` | AD, AU | AD | AD | none | AD | Permission changes are audited and require admin. |
| `security` | `AuditLog` | AD, AU | system | none | none | AD | Append-only. Auditor is read-only including audit log. |
| `presentation` | `Dashboard` | V, M, QE, AD, AU | AD | V, M, QE, AD | none | AD | Users may update only own layout/preferences; global dashboards are admin-managed. |
| `presentation` | `Report` | V, M, QE, AD, AU | M, QE, AD | AD | none | AD | Report generation/export is allowed; template management is admin-only. |
| `system` | `SystemConfiguration` | AD, AU | AD | AD | none | AD | Includes preferences defaults, retention, feature flags, and security settings. |
| `live_monitor` | `Stream` | M, QE, AD, AU | none | none | none | AD | WebSocket replay of already-seeded measurements (`docs/design/live-monitor-panel.md`); read-only, same auth as any REST endpoint, never writes to `measurement_results`. |

## Minimum Demo Permissions

The client-facing demo needs only this path:

1. `viewer`, `metrologist`, `quality_engineer`, `admin`, and `auditor` can log in.
2. `metrologist` imports a fictitious CSV/XLSX file.
3. The system creates immutable measurements, compliance results, SPC/risk
   outputs, alerts, and recommendations.
4. `metrologist` reviews runs and recommendations but cannot decide.
5. `quality_engineer` accepts or rejects a recommendation with a comment.
6. The system records the decision and audit trail.
7. `viewer` sees dashboards/reports only.
8. `auditor` can inspect all read-only evidence, including `AuditLog`.
9. `admin` can seed/manage demo users and master data.

## Permission Tokens

Backend implementation should use explicit permission tokens rather than role
checks scattered across endpoint code. The recommended token format is:

```text
<module>.<resource>.<action>
```

Examples:

```text
catalog.part_number.read
catalog.specification.create
measurement.imported_file.create
measurement.measurement_result.read
intelligence.recommendation.decide
security.audit_log.read
system.configuration.administer
```

Endpoint code may use role convenience helpers only if they resolve to these
tokens internally. Frontend route guards must mirror backend permissions for
navigation only; the backend remains authoritative.

## Endpoint Guard Rules

- Public unauthenticated routes: `/health`, login, refresh-token exchange.
- All `/api/v1/*` routes require authentication unless explicitly documented.
- Every route declares one or more permission tokens.
- State-changing routes require audit logging.
- Import routes require both RBAC and upload validation.
- Decision routes require `intelligence.recommendation.decide`.
- Measurement correction routes, if added later, must create superseding rows
  and must never update or delete historical measurements.

## Test Contract For F4.2

F4.2 should convert this matrix into parametrized tests:

- Role x endpoint expected `200/201/204` or `403`.
- Unauthenticated access to protected endpoints returns `401`.
- `viewer`, `metrologist`, and `auditor` cannot call any decision endpoint.
- `auditor` has no successful write/update/decide/administer endpoint.
- No role can update or delete `MeasurementRun`, `MeasurementSample`, or
  `MeasurementResult`.
- Any successful write to master data, users, imports, recommendations,
  decisions, or configuration creates an `AuditLog` entry.
