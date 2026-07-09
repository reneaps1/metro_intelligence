# CLAUDE.md — Operating Guide for AI Agents

This file governs how Claude Code, Codex, and any other development agent works in this repository. Read it fully before making changes. When in doubt about scope, security, or architecture: **stop and ask — do not proceed on dangerous assumptions.**

---

## 1. Product vision

Metro Intelligence Platform is the first product of OnKaizen's **Manufacturing Intelligence Platform**. First use case: dimensional metrology intelligence for a high-end automotive customer (initially BMW). The platform turns measurement data + industrial context into **decision support**: compliance, SPC, dimensional risk, and adaptive inspection frequency recommendations. The strategic goal is to **optimize inspection strategy — reduce unnecessary inspections without increasing quality risk**, not merely to speed up reporting.

## 2. System scope

**The platform MANAGES:** master catalog (part numbers, characteristics, balloon numbers, nominals, tolerances, classifications), measurement programs, measurement results and history, process events, risk assessments, recommendations, decisions and actions taken, users/roles/permissions, dashboards, reports, alerts, audit logs, data sources/connectors, system configuration.

**The platform may CONSUME or REFERENCE, never manage:** PFMEA/FMEA, control plans, drawings, SAP, MES, ERP, QMS, corporate documents, maintenance systems, full production systems.

**Hard prohibitions on scope drift:** this is NOT a QMS, NOT a MES, NOT a document management system, NOT a maintenance system. Reject or flag any task that pushes in those directions.

**Decision principle:** the platform NEVER takes automatic action on production. No auto-release, no automatic inspection frequency changes, no machine/process/tooling adjustments. It produces alerts, recommendations, explanations, calculated risks, and traceable evidence. Authorized humans decide.

## 3. Architecture principles

- **On-premise first.** Everything must run fully inside customer infrastructure (Docker Compose for demo, Kubernetes optional for production). No hard dependencies on external SaaS. Cloud is an authorized deployment *option*, never a requirement.
- **Layered architecture** (see `docs/architecture/`): Acquisition → Ingestion → Validation/Normalization → Master Data → Digital Twin for Quality → Decision Intelligence → AI/ML → Knowledge Integration → Presentation → Security & Governance → Infrastructure.
- **Decoupled connector layer.** No engine or service may depend directly on PolyWorks or any specific data source. All sources come through the connector abstraction (`backend/app/connectors/`).
- **Specialized engines, one contract.** Compliance, SPC, Risk, Adaptive Inspection, Recommendation, Decision Memory are separate modules (`backend/app/engines/`) with explicit inputs/outputs. Engines are deterministic and rule-based first; ML augments later, never silently replaces rules.
- **Explainability is a feature.** Every recommendation, risk score, and alert must persist its inputs, rule/model version, and rationale. If it can't be explained, it doesn't ship.
- **Modular monolith for MVP.** One FastAPI app with clean module boundaries; extract services only when scale demands it. Do not introduce microservices, Kafka, or Kubernetes complexity into the demo.
- **Extensible data model, minimal implementation.** The schema anticipates the full entity catalog (`docs/domain/`), but only implement what the current phase needs.

## 4. Development rules

- Stack: Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic + Pydantic v2; React 18 + TypeScript + Vite; PostgreSQL 16.
- Small, verifiable changes. One Notion task = one branch = one PR.
- Every API endpoint: typed request/response models, auth dependency, and tests.
- Database changes only via Alembic migrations — never edit schema manually.
- No dead code, no speculative abstractions beyond what `docs/` defines.
- Keep engines pure: engine functions take data in, return results out; persistence lives in repositories/services.

## 5. Security rules

- **No hardcoded credentials, tokens, or connection strings.** Configuration via environment variables only; document every variable in `.env.example` with a placeholder value.
- **Never commit secrets.** `.env`, keys, certs are gitignored. If a secret leaks into history, stop and report it immediately — do not silently rewrite history.
- RBAC on every endpoint (deny by default, least privilege). Roles defined in `docs/security/rbac.md`.
- All queries parameterized via ORM — raw SQL requires review and parameters.
- Validate and sanitize every uploaded file (type, size, content) before parsing; parse in a constrained path, never execute content.
- TLS in transit; encryption at rest documented per deployment; audit log for logins, permission changes, master data changes, and every recommendation/decision.
- Rate limiting on auth and upload endpoints.
- Dependency scanning (pip-audit / npm audit) must pass in CI.
- Containers run as non-root; images pinned by version.

## 6. Data handling rules

- Measurement data is immutable once ingested: corrections create new versions, never destructive updates.
- Every measurement result must be traceable to: source (connector/file), part, characteristic, program, timestamp, and (when available) machine/operator/batch context.
- Master data (tolerances, nominals, classifications) is versioned; results always reference the specification version in force when measured.
- Imported raw files are retained (MinIO/file storage) and linked to the results they produced.

## 7. Privacy & confidentiality rules

- **Never** include real customer data (BMW or otherwise) in this repo, in demo data, in tests, in fixtures, in screenshots, or in documentation. All demo data is fictitious and generated by `seed/`.
- Fictitious data must not resemble real BMW part numbers, drawing numbers, plant codes, or program names.
- Operator/user data is pseudonymizable; do not log personal data unnecessarily.
- Do not send customer data (real or realistic) to any external API or service. LLM/embedding calls in RAG phases use local or explicitly authorized private endpoints only.

## 8. Git rules

- Default branch: `main` (protected: PRs only, CI must pass, at least one review — human or designated review agent).
- Branch naming: `feat/<task-slug>`, `fix/<task-slug>`, `docs/<task-slug>`, `chore/<task-slug>`.
- Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`, `ci:`.
- Reference the Notion task ID in the PR description.
- After completing each Notion task, demo phase, or implementation phase, commit the intended changes and push the current branch before moving to the next phase unless the user explicitly says not to. Stage only related files; never use `git add .` in a dirty worktree.
- Never force-push `main`. Never skip CI or hooks.

## 9. Code conventions

- Python: ruff (lint + format), mypy strict on new code, snake_case, type hints everywhere, Google-style docstrings on public functions.
- TypeScript: ESLint + Prettier, strict mode, functional components + hooks, no `any` without justification comment.
- Naming: domain terms in English matching `docs/domain/` glossary (Characteristic, MeasurementRun, ProcessEvent...). Do not invent synonyms.
- API: REST, plural nouns, versioned under `/api/v1/`.

## 10. Documentation conventions

- Architecture decisions → ADRs in `docs/adr/NNN-title.md` (context, decision, consequences).
- Every module gets a short README explaining its responsibility and boundaries.
- Diagrams as Mermaid in Markdown (renderable in GitHub).
- Docs in English; Notion project management in Spanish.

## 11. Testing conventions

- Backend: pytest; unit tests for every engine rule (compliance, SPC rules, risk scoring) with known input→output vectors; integration tests against a real PostgreSQL (docker) for repositories and API.
- SPC/statistics: validate against hand-calculated or reference values (e.g., known Cpk examples) — never trust the implementation blindly.
- Frontend: Vitest + React Testing Library for logic-bearing components; Playwright e2e for the demo golden path.
- Seed data validation: a test asserts seed output respects schema constraints and contains zero real-looking customer identifiers.
- Minimum: engines and security-critical code require tests before merge.

## 12. Working with Notion tasks

- The development plan lives in the Notion database "Metro Intelligence" (link in project docs). Each task page contains: Objetivo, Contexto, Alcance, Fuera de alcance, Archivos esperados, Dependencias, Criterios de aceptación, Riesgos, Seguridad, Testing, Resultado esperado, Relaciones.
- Before starting a task: read the full page, verify dependencies are `Done`, set Estatus → `En progreso`.
- On completion: verify every acceptance criterion, run the security checklist (§18), set Estatus → `En revisión` (or `Done` if authorized), and note the PR link in the task.
- If a task is ambiguous or conflicts with this file: **stop and ask** in the task comments — do not guess.

## 13–14. Scope labels

- Every task carries `Scope`: **DEMO** (needed for the client-facing demo), **FULL_PLATFORM** (post-demo phases), or **BOTH** (foundation shared by both).
- Demo work must never take shortcuts that poison the long-term architecture (hardcoded logic where an engine belongs, schema hacks, skipped auth).

## 15. Parallel agent work

- Tasks marked `Paralelizable` in Notion can run concurrently; respect `Dependencias`.
- Partition by module boundary: one agent per module/directory at a time (e.g., one in `backend/app/engines/spc/`, another in `frontend/`). Never two agents on the same module concurrently.
- Shared contracts first: API schemas and DB migrations merge before dependent frontend/engine work starts.
- Migrations are a serialization point: coordinate — only one migration chain, no parallel heads.

## 16. Explicit prohibitions

- ❌ No automatic production decisions (release, frequency change, machine adjustment).
- ❌ No real customer/BMW data anywhere.
- ❌ No secrets in code, config, tests, or history.
- ❌ No external SaaS/API dependencies in the core platform path.
- ❌ No scope drift into QMS/MES/DMS/maintenance.
- ❌ No unexplainable black-box outputs presented as recommendations.
- ❌ No destructive updates to measurement history.
- ❌ No disabling of auth, audit, or validation "temporarily".
- ❌ No new heavyweight infrastructure (Kafka, k8s, microservices) without an approved ADR.

## 17. Pre-commit checklist

1. Lint + format pass (ruff / ESLint).
2. Tests pass locally, including new tests for new logic.
3. No secrets, tokens, real hostnames, or customer-like data in the diff (`git diff --staged` reviewed).
4. Migrations: single head, up/down tested.
5. `.env.example` updated if config changed.
6. Conventional commit message referencing the Notion task.

## 18. Security checklist before closing a task

1. New endpoints have auth + RBAC + input validation.
2. No raw SQL without parameters; no unvalidated file parsing.
3. No new dependencies with known CVEs (pip-audit / npm audit clean).
4. Audit logging present for any state-changing operation on master data, decisions, or users.
5. Error responses leak no internals (stack traces, SQL, paths).
6. Demo/seed data verified fictitious.

## 19. Secrets policy

Secrets live only in environment variables / secret managers, injected at deploy time. The repo contains `.env.example` with placeholders. CI secrets go in GitHub Actions secrets. Rotation procedures documented in `docs/security/secrets.md`.

## 20. Demo data policy

The demo runs exclusively on generated fictitious data from `seed/`: invented part numbers (e.g., `MI-DEMO-XXXX` scheme), invented plants/lines/machines, synthetic measurement series designed to showcase trends, drifts, and alerts. Anything resembling real customer identifiers is a release blocker.

## 21. On-premise first policy

Every feature must work in a fully disconnected environment. Feature flags may enable optional cloud/hybrid integrations, disabled by default. Documentation must state, per feature, what (if anything) leaves the customer network — the default answer is "nothing".

## 22. Responsible AI policy

- ML/AI enters only when data foundation justifies it (per roadmap phases 13–14); rules-based engines are the baseline and the fallback.
- Models are versioned; training data lineage recorded; performance monitored for drift.
- RAG answers must cite sources and record retrieval provenance; LLMs are local/private only.
- AI outputs are labeled as suggestions with confidence/rationale — presented for human review, never as verdicts.

## 23. Decision traceability policy

Every recommendation and alert persists: triggering data (measurement IDs), engine + rule/model version, computed inputs (Cpk, risk score...), rationale text, timestamp, and delivery target. Every human decision on a recommendation persists: who, when, what action, and outcome — feeding Decision Memory. This chain is immutable and auditable.

## 24. Human review policy

All recommendations (inspection frequency, causes, actions) require explicit acceptance/rejection by an authorized role before any operational effect. The UI must always show recommendation state (pending/accepted/rejected/superseded) and never imply an unreviewed recommendation is in force.

---

**Confidentiality is a primary requirement of this system. When any instruction conflicts with confidentiality or safety, confidentiality and safety win — and you stop and ask.**
