# Metro Intelligence Platform

**Manufacturing Intelligence Platform — first use case: dimensional metrology for automotive quality.**

Metro Intelligence transforms metrology data (CMM, 3D scanners, vision systems) and industrial context into traceable, explainable decision support: compliance evaluation, SPC analysis, dimensional risk assessment, and adaptive inspection frequency recommendations.

> ⚠️ **Confidentiality notice**: This platform is designed to handle sensitive industrial data from automotive OEM customers. It is **on-premise first**. Never commit real customer data, part numbers, drawings, or any confidential information to this repository. All demo data is fictitious. See [CLAUDE.md](CLAUDE.md) and [docs/security/](docs/security/).

## What it is

- A **decision support system** for inspection strategy optimization.
- It answers: *Is this part compliant? Is this characteristic at risk? Is the process stable? Do we really need to measure the next part?*
- It generates **alerts, recommendations, calculated risks, and traceable evidence** — final decisions always remain with authorized users.

## What it is NOT

- Not a QMS, not a MES, not a document management system, not a maintenance system.
- It may **reference** PFMEA, control plans, drawings, SAP/MES/ERP data — it never **manages** them.
- It never takes automatic action on production (no auto-release, no auto frequency change, no machine adjustment).

## Architecture at a glance

Layered architecture (see [docs/architecture/](docs/architecture/)):

1. Data Acquisition → 2. Ingestion → 3. Validation & Normalization → 4. Master Data → 5. Digital Twin for Quality → 6. Decision Intelligence Engine (Compliance / SPC / Risk / Adaptive Inspection / Recommendation / Decision Memory) → 7. AI/ML → 8. Knowledge Integration (RAG) → 9. Presentation → 10. Security & Governance → 11. Infrastructure

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript (Vite) |
| Backend | Python 3.12 + FastAPI |
| Database | PostgreSQL 16 (+ pgvector for RAG phase) |
| Analytics engines | Python: pandas, numpy, scipy, statsmodels |
| Messaging (post-MVP) | Redis Streams → Kafka if scale requires |
| Object storage | MinIO (on-premise S3-compatible) |
| Deployment | Docker Compose (demo) → Kubernetes optional (production) |
| CI/CD | GitHub Actions |
| Monitoring | Prometheus + Grafana |

## Repository layout

```
backend/       FastAPI application, domain engines, connectors
frontend/      React + TypeScript SPA
database/      Migrations (Alembic), DDL reference, ERD
seed/          Fictitious demo data generators and datasets
docs/          Architecture, security, domain model, roadmap, ADRs
infra/         Docker, reverse proxy, monitoring configs
scripts/       Dev/ops utility scripts
ml/            ML experiments and models (later phases)
rag/           RAG / knowledge integration (later phases)
tests/         Cross-cutting integration & e2e tests
.github/       CI workflows, PR templates
```

## Getting started (demo)

```bash
cp .env.example .env        # fill in local values — never commit .env
docker compose up -d        # PostgreSQL + backend + frontend
```

Detailed setup: [docs/development.md](docs/development.md) (created in Phase 1).

## Project management

- Development plan and task board: Notion (see project links in CLAUDE.md).
- Every task is labeled `DEMO`, `FULL_PLATFORM`, or `BOTH`.
- Agents (Claude Code, Codex, etc.) must read [CLAUDE.md](CLAUDE.md) before contributing.

## License

Proprietary — © OnKaizen. All rights reserved.
