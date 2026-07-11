# seed/

Fictitious demo data generation (Phase 3). See docs/seed-data-strategy.md.

- `config/scenarios.yaml` — the five measurement-pattern scenarios (stable_capable, slow_drift, shift_after_event, high_variance, outlier_nok) and their generator parameters.
- `generators/` — `base.py` provides the seeded RNG (`make_rng`), the shared `SeedContext` (including an `artifacts` dict generators use to hand data to each other), and a `register_generator` hook.
  - `catalog.py` (F3.2): 3 product families, 8 parts, characteristics/tolerances/classifications, demo plant/lines/machines.
  - `measurements.py` (F3.3): ~90 days of measurement history, cycling every characteristic through all five scenarios so each pattern shows up in the demo.
  - Process events, demo users, and recommendation/decision history (F3.4) aren't registered yet.
- `sample_files/` — generated CSV/Excel files used to demo the live import flow (F3.5).
- `db.py` — DB connection (same env-var convention as `backend/alembic/env.py`) and `reset_database()` (TRUNCATE ... CASCADE across every mapped table).
- `__main__.py` — CLI: `python -m seed --reset [--scenario <name>]`. Every registered generator runs on every invocation (they each cover all five scenarios internally); `--scenario` currently only validates the name against `scenarios.yaml` and is a hook for a future "generate just this pattern" mode.

## Usage

```bash
pip install -r seed/requirements.txt -r backend/requirements.txt
export DATABASE_URL=postgresql+psycopg://metro_app:changeme@localhost:5432/metro_intelligence
python -m seed --reset
```

Same seed → same data, every time (`config/scenarios.yaml`'s `default_seed`, override with `--seed`). Never real customer data — CI runs the confidentiality lint against this directory.
