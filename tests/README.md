# tests/

Cross-cutting test suites (module-level unit tests live inside backend/ and frontend/):

- `e2e/` — Playwright golden-path suites (light + dark theme, role matrix).
- `security/` — auth abuse, upload abuse, RBAC matrix suites.
- `seed_validation/` — schema + statistical sanity + confidentiality lint over seed output.

See docs/testing-strategy.md for gates.
