# Roadmap

Full task-level plan lives in Notion (Spanish). This file is the stable summary. Scope labels: **DEMO** (client-facing demo), **FULL_PLATFORM**, **BOTH**.

## Guiding sequence

**First: a sellable demo (Phases 0–6 subset) on a sound architectural base. Then: platform depth by phases.** Demo work never poisons long-term architecture (CLAUDE.md §13–14).

| Phase | Name | Scope | Outcome |
|---|---|---|---|
| 0 | Technical discovery & architecture definition | BOTH | Decisions closed: stack, deployment models, domain model draft, this repo's docs |
| 1 | Repo setup, base docs & policies | BOTH | Repo structure, CLAUDE.md, CI skeleton, branch protection, design system |
| 2 | Conceptual model & initial DDL | BOTH | Alembic migrations for demo subset; ERD published |
| 3 | Seed data (fictitious) | DEMO | Generators producing parts, characteristics, tolerances, realistic measurement series with injected drifts/NOKs/events |
| 4 | Backend MVP | BOTH | FastAPI app: auth+RBAC, catalog CRUD, CSV/Excel import, measurements API, audit log |
| 5 | Frontend MVP | BOTH | React shell (sidebar, theming, profile/preferences), catalog, imports, measurement views |
| 6 | Dashboards & reports | DEMO | Operational + executive dashboards, trend charts, basic PDF/export |
| 7 | Compliance engine | BOTH | OK/NOK evaluation vs versioned specs, disposition rollup (demo uses its first iteration) |
| 8 | SPC engine | BOTH | Cp/Cpk/Pp/Ppk, control charts, Nelson + Western Electric rules (demo shows subset) |
| 9 | Risk engine | BOTH | Composite risk score + factors (demo shows first iteration) |
| 10 | Adaptive inspection engine | BOTH | Frequency recommendations + projected risk (demo shows first iteration) |
| 11 | Enterprise security | FULL_PLATFORM | SSO/LDAP, MFA, hardening, secrets mgmt, immutable audit, pen-test fixes |
| 12 | Real integrations | FULL_PLATFORM | PolyWorks connector (SDK/DB/export), watched folders, connector framework hardening |
| 13 | Experimental ML | FULL_PLATFORM | Anomaly detection, drift prediction, adaptive sampling models — offline first, shadow mode |
| 14 | RAG & knowledge integration | FULL_PLATFORM | Local LLM + pgvector/Qdrant, cited answers over referenced docs |
| 15 | Hardening, testing & on-prem deployment | FULL_PLATFORM | DR, backups, monitoring, load tests, security scans, install runbooks |
| 16 | Production readiness | FULL_PLATFORM | Pilot at customer, acceptance, support/ops handbook, versioning & release process |
| 17 | Manufacturing Intelligence evolution | FULL_PLATFORM | Multi-use-case abstraction, new data domains, product roadmap v2 |

## Demo definition (client-facing)

Golden path: **login (role-aware) → import measurement file → catalog with balloon/tolerances → OK/NOK results → trend chart with SPC limits → risk panel → frequency recommendation with rationale → engineer accepts/rejects (traceable) → operational & executive dashboards — in light and dark mode.**

Demo phases: 0,1,2,3 + MVP slices of 4,5,6 + first iterations of 7,8,9,10. Everything fictitious (`MI-DEMO-*` data), Docker Compose single host.

## Parallelization rules

- Contracts first: migrations + API schemas merge before dependent work.
- One agent per module; migrations are a serialization point.
- Engines (7–10) parallelize cleanly after Phase 2+4 core; frontend (5,6) parallelizes against mocked API contracts.
