# Testing Strategy

## Pyramid

1. **Unit (largest layer)** — pytest. Every engine rule tested with known input→output vectors: tolerance evaluation edge cases (on-limit values, unilateral tolerances), Cp/Cpk/Pp/Ppk against hand-calculated reference values, each Nelson/Western Electric rule with synthetic series that do and don't trigger, risk score factor weighting, frequency recommendation thresholds.
2. **Integration** — pytest against real PostgreSQL (docker service in CI): repositories, migrations (up/down, single head), API endpoints with auth/RBAC matrix (each role × each endpoint → expected 200/403), import pipeline with valid/corrupt/malicious files.
3. **E2E** — Playwright: the demo golden path (login → import → results → dashboard → recommendation decision) in light *and* dark theme; role-based visibility checks.
4. **Frontend unit** — Vitest + React Testing Library for stateful components (tables, forms, chart data mappers).

## Security testing (CI-gated)

- Dependency audit: `pip-audit`, `npm audit` — fail on high/critical.
- Secret scanning: gitleaks on every PR.
- Container scan: trivy on built images.
- Auth tests: brute-force lockout, expired/forged JWT, privilege escalation attempts.
- Upload tests: oversized files, wrong magic bytes, formula-injection CSV, zip bombs → all rejected with clean errors, quarantined, audited.

## Data-quality tests

- Seed validation suite (see seed-data-strategy.md).
- Property-based tests (hypothesis) for normalization: any parsable measurement row → canonical model or explicit quarantine, never silent drop.

## Gates

- PR merge requires: lint (ruff/ESLint), typecheck (mypy/tsc), unit+integration green, security scans green.
- Engines and security-critical code: tests required *before* merge, target ≥90% branch coverage on engine modules.
- E2E runs nightly and before any demo/release tag.
