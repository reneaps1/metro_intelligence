# database/

Reference material for the physical schema. The **authoritative** schema is `backend/alembic/` migrations.

- `erd/` — exported ERD diagrams per module (from docs/domain/conceptual-model.md).
- `ddl-reference/` — generated DDL snapshots per release (read-only, for customer DBA review).
- `policies.md` — naming conventions, partitioning plan for `measurement_result`, audit table rules (append-only).
