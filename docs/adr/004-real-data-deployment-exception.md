# ADR-004: Real production data in the deployment database

**Status:** Accepted · 2026-11-13

## Context
CLAUDE.md §7, §16 and §20 require every demo, seed, fixture and document to use fictitious data. The product owner decided to stop showing generated demo data and to run the platform on one real production line's inspection logs, so that users see real per-step quality results. The logs come from the line's station PLC exports (one CSV per day per station) and include customer part identifiers, drawing references and production volumes.

## Decision
1. Real production data may be loaded **into a deployment database** (PostgreSQL + MinIO raw-file bucket) by the owner's explicit instruction. This is the only exception to §7/§16/§20.
2. The exception does **not** extend to the repository. Real data files, real identifiers (line codes, station folder names, part and drawing numbers, customer or supplier names), real tolerances, derived samples and screenshots of real data never enter git, tests, fixtures, docs or CI logs.
3. Everything that is customer-specific is supplied at run time from files outside the repository:
   - the ingest config (`INGEST_CONFIG_PATH`): line, stations, recipe scope, timezone;
   - the specification file passed to `import_specifications`;
   - the data directory (`LINE_DATA_DIR`), mounted read-only.
   The repository ships only `backend/app/ingest/config.example.yaml` and `backend/app/ingest/specs.example.yaml` with `MI-DEMO-*` values.
4. Tests use synthetic files generated in the same file format (`backend/tests/fixtures/line_csv_factory.py`), with fictitious ids and values.
5. Raw source files are retained in MinIO and linked to the results they produced (§6). Database dumps and the raw bucket are treated as customer confidential: access limited to the owner's administrators, backups encrypted at rest.

## Consequences
+ Users see real line behaviour; the per-step views are validated against real volumes.
+ The repository stays shareable: CI, docs and fixtures remain free of customer data.
− The deployment now holds customer IP. Network exposure, access control and backups of that deployment must follow `docs/security/security-architecture.md` for confidential data, and the owner is responsible for the customer's authorization to host it there.
− Demo resets no longer restore a fictitious dataset; `purge_domain_data` removes domain data and the ingest CLIs reload the real one.
