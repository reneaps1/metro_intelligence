# seed/

Fictitious demo data generation (Phase 3). See docs/seed-data-strategy.md.

- `config/scenarios.yaml` — the five measurement-pattern scenarios (stable_capable, slow_drift, shift_after_event, high_variance, outlier_nok) and their generator parameters.
- `generators/` — `base.py` provides the seeded RNG (`make_rng`), the shared `SeedContext`, and a `register_generator` hook. Deterministic Python generators for catalog, measurement series, process events, users, and recommendation history (F3.2–F3.4) register into this framework — none exist yet.
- `sample_files/` — generated CSV/Excel files used to demo the live import flow (F3.5).
- `db.py` — DB connection (same env-var convention as `backend/alembic/env.py`) and `reset_database()` (TRUNCATE ... CASCADE across every mapped table).
- `__main__.py` — CLI: `python -m seed --reset --scenario <name>`.

## Usage

```bash
pip install -r seed/requirements.txt -r backend/requirements.txt
export DATABASE_URL=postgresql+psycopg://metro_app:changeme@localhost:5432/metro_intelligence
python -m seed --reset --scenario stable_capable
```

Same seed → same data, every time (`config/scenarios.yaml`'s `default_seed`, override with `--seed`). Never real customer data — CI runs the confidentiality lint against this directory.
