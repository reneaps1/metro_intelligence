# backend/

FastAPI modular monolith (built in Phase 4). Target layout:

```
app/
  api/v1/          # Routers (auth, catalog, imports, measurements, risk, recommendations, admin)
  core/            # Config, security (JWT, RBAC deps), logging
  models/          # SQLAlchemy models by module (org, catalog, measurement, context, intelligence, security)
  schemas/         # Pydantic request/response models
  repositories/    # DB access
  services/        # Orchestration / use cases
  engines/         # compliance/ spc/ risk/ adaptive_inspection/ recommendation/ decision_memory/  (pure functions)
  connectors/      # Connector abstraction + implementations (manual upload, watched folder, polyworks…)
alembic/           # Migrations (single head — serialization point)
tests/
```

Rules: engines are pure (no DB access); every endpoint has auth + RBAC + tests; schema changes only via Alembic. See /CLAUDE.md.
