# Database Policies

Naming conventions, partitioning plan, and immutability rules for the physical schema. The authoritative schema is `backend/alembic/versions/`; this document explains the *why* and the operational maintenance those migrations assume.

## 1. Naming conventions

- Tables: `<module>_<plural_entity>` (e.g. `catalog_characteristics`, `measurement_results`).
- Constraint names follow SQLAlchemy's naming convention (`backend/app/models/base.py::NAMING_CONVENTION`): `pk_<table>`, `uq_<table>_<column>`, `fk_<table>_<column>_<referred_table>`, `ck_<table>_<name>`, `ix_<label>`. Postgres identifiers cap at 63 bytes; names that would exceed it are truncated with a short deterministic hash suffix. Hand-written migrations that can't use `op.create_table` (e.g. partitioned tables) hardcode the exact truncated name so the DDL stays in lockstep with what SQLAlchemy computes from the ORM models — see `0003_measurement.py` for the pattern.
- Every table gets `created_at`; mutable tables also get `updated_at` (`server_default=now()`, `onupdate=now()`).

## 2. Partitioning: `measurement_result`

`measurement_result` is the highest-volume table in the system (CLAUDE.md §4, domain notes §4) and is declared with native PostgreSQL **range partitioning on `measured_at`**, monthly granularity.

- Migration `0003_measurement` pre-creates monthly partitions for calendar year **2026** (`measurement_results_2026_01` … `measurement_results_2026_12`) plus a `measurement_results_default` catch-all partition so inserts never fail while new partitions are pending.
- **Maintenance job (required before Dec 2026):** create the next calendar year's monthly partitions ahead of time via a new Alembic migration (never by hand-editing a shipped one). Recommended lead time: 2 months before the first missing partition would receive data. Pattern to follow:
  ```sql
  CREATE TABLE measurement_results_2027_01
  PARTITION OF measurement_results
  FOR VALUES FROM ('2027-01-01') TO ('2027-02-01');
  ```
- Never insert directly into `measurement_results_default` at volume — treat non-empty rows there as a signal that partition maintenance is late, and migrate them into a proper monthly partition during the next maintenance window.
- Every partitioned-table query pattern must go through the parent `measurement_results` table (never a specific partition by name) so the planner can prune partitions using `measured_at` predicates. The mandatory index is `(characteristic_id, measured_at)` for time-series-per-characteristic queries; it is created once on the parent and Postgres clones it to every partition automatically.
- The primary key is the composite `(id, measured_at)` — Postgres requires the partition key in any unique/primary constraint on a partitioned table. `id` (UUIDv7) remains globally unique in practice because it is generated application-side.

## 3. Immutability rules (append-only / no destructive updates)

Two tables enforce immutability at the database level via a `BEFORE UPDATE OR DELETE` trigger that unconditionally raises — this works regardless of role privileges (including table owners), unlike a `REVOKE`-only approach, and is defense-in-depth alongside an explicit `REVOKE UPDATE, DELETE ... FROM PUBLIC`:

- `security_audit_log` (migration `0001_org_security`) — corrections are never needed; the log is append-only forever.
- `measurement_results` (migration `0003_measurement`) — corrections **insert a new row** with `supersedes_id` pointing at the row being corrected. `supersedes_id` is a bare column, not an enforced foreign key: PostgreSQL cannot express a normal FK into a partitioned table's primary key without also carrying the partition column, and a self-referencing FK across partitions isn't practical here. Referential integrity for `supersedes_id` is an application/service-layer responsibility.

Since PostgreSQL 11, a row-level trigger declared on a partitioned parent table is automatically cloned to every partition, including ones created later — no per-partition trigger maintenance is needed.

## 4. Roles

The demo ships with a single application database role (superuser-free, standard `INSERT/SELECT/UPDATE/DELETE` grants where the schema allows). Immutability on the two append-only tables above is enforced by trigger, not by role-specific grants, precisely so it holds regardless of which role the application connects as. A dedicated least-privilege per-table role scheme is deferred to Phase 11 (Enterprise security) — introducing it earlier would be scope creep the demo doesn't need (CLAUDE.md §13–14).
