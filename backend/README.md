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

## Audit trail (F4.3 / MI-23)

CLAUDE.md §5/§23 require an audit entry for every login, permission change,
and write to master data, users/roles, or decisions. `app/services/audit_service.py`
is the single place that writes `security_audit_log` rows -- do not construct
`AuditLog` rows directly in a service or repository.

Pattern for any endpoint that writes master data, decisions, or user/role changes:

```python
from app.services.audit_service import get_audit_context, record_change

@router.patch("/specs/{spec_id}")
def update_spec(
    spec_id: uuid.UUID,
    payload: SpecUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("catalog.characteristic_spec", "update")),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> SpecOut:
    before = {"nominal": spec.nominal, "tolerance": spec.tolerance}
    # ... apply the update ...
    after = {"nominal": spec.nominal, "tolerance": spec.tolerance}
    record_change(
        db, audit_ctx,
        action="spec_updated", entity_type="catalog.characteristic_spec",
        entity_id=spec.id, before=before, after=after,
    )
    db.commit()
    return spec
```

- `get_audit_context` resolves the real actor (from the JWT via `get_current_user`) and client IP -- never pass a guessed/hardcoded actor.
- `record_change` diffs `before`/`after` and only stores the fields that changed; `record_event` is for actions without a before/after pair (e.g. a decision or a create).
- Known-sensitive keys (`password`, `password_hash`, `token`, `secret`, ...) are stripped automatically, but callers should still avoid passing more than the fields relevant to the change.
- `/auth/*` login/logout events use the lower-level `write_audit_log` directly (no authenticated actor exists yet for a failed login) -- everything else should go through `record_event`/`record_change`.
