# seed/

Fictitious demo data generation (Phase 3). See docs/seed-data-strategy.md.

- `generators/` — deterministic Python generators (fixed random seed) for catalog, measurement series with injected patterns (drift, shift-after-event, high variance, stable/capable), process events, users, recommendation history.
- `sample_files/` — generated CSV/Excel files used to demo the live import flow.

Never real customer data. CI runs the confidentiality lint against this directory.
