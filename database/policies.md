# Database Policies

## Naming conventions

- Tables: `<module>_<plural_noun>` (e.g. `catalog_characteristics`, `measurement_results`).
- Constraints follow the Alembic naming convention in `app/models/base.py` (`pk_`, `fk_`, `uq_`, `ck_`, `ix_`).
- Every module's tables are prefixed with the module name (`org_`, `security_`, `catalog_`, `measurement_`, `context_`, `intelligence_` when it lands in F2.4).

## Append-only / insert-only tables

Two tables enforce immutability with a `BEFORE UPDATE OR DELETE` trigger that unconditionally raises, applied at the partitioned/plain parent so it cascades to every partition automatically (PostgreSQL 11+ trigger inheritance) and can't be bypassed by writing to a partition directly or by DB role:

| Table | Rule | Correction path |
|---|---|---|
| `security_audit_log` | Append-only. | N/A — audit entries are never corrected. |
| `measurement_results` | Insert-only. | Insert a new row with `supersedes_id` pointing at the row being corrected. |

## `measurement_results` partitioning plan

Partitioned by `RANGE (measured_at)`, monthly, since migration `0003_measurement`:

- Partitions are named `measurement_results_YYYY_MM`.
- Migration `0003` pre-creates all twelve 2026 partitions plus a `measurement_results_default` catch-all (`PARTITION OF ... DEFAULT`) so no write is ever rejected for lacking a partition.
- **Operational rule:** create each new month's partition *before* it starts (e.g. a monthly ops job or the next migration in the chain), then move any rows that landed in `measurement_results_default` into it with `ALTER TABLE measurement_results DETACH PARTITION ... / ATTACH PARTITION ...` or a manual `INSERT ... SELECT` + `DELETE` from the default partition (the trigger blocks `DELETE` on the parent's public interface — operate on the default partition directly as a superuser/maintenance role, which the trigger's `RAISE EXCEPTION` still applies to; partition maintenance is a schema migration, not an application code path).
- The primary key is composite (`id`, `measured_at`) because PostgreSQL requires the partition key in every unique constraint on a partitioned table. Application code must always carry `measured_at` alongside `id` when referencing a specific result row.
- The `(characteristic_id, measured_at)` index exists on the parent and is created on every partition automatically — this is what makes trend/SPC queries efficient across partition boundaries.
