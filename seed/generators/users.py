"""F3.4 (MI-19): one demo user per RBAC role (docs/security/rbac.md), all on
the deliberately artificial `.local` domain (docs/seed-data-strategy.md).
SEED_DEMO_USER_PASSWORD exists so seeding fails loudly if nobody has set an
intended demo password (CLAUDE.md §5: no hardcoded credentials) -- it is
hashed with F4.2's own argon2id helper (app.core.security.hash_password), the
same one the real /auth/login endpoint verifies against, so every demo user
can actually sign in through F5.4's real login screen with this one shared
password.

The five system roles themselves are *not* created here — migration 0001
(backend/alembic/versions/0001_org_security_migration.py) already
bulk_inserts them along with their permissions, since RBAC is static schema
data (docs/security/rbac.md), not something a demo dataset should own. This
generator only looks them up by name and attaches a demo user to each."""
from __future__ import annotations

import os

from sqlalchemy import select

from app.models import Role, User, UserRole

from seed.generators.base import SeedContext, register_generator

# (role code, description, email, display name) — role descriptions mirror
# docs/security/rbac.md's role table.
ROLE_DEFINITIONS = [
    ("viewer", "Read-only user for dashboards and reports.", "karla.jimenez@demo.local", "Karla Jiménez"),
    (
        "metrologist",
        "Runs the metrology workflow: imports files, reviews measurement runs, views recommendations and alerts.",
        "ana.garcia@demo.local",
        "Ana García",
    ),
    (
        "quality_engineer",
        "Owns engineering review: manages inspection plans/frequencies, evaluates risks, and accepts or rejects recommendations.",
        "sofia.mendez@demo.local",
        "Sofía Méndez",
    ),
    (
        "admin",
        "Administers master data, users, roles, permissions, connectors, configuration.",
        "luis.torres@demo.local",
        "Luis Torres",
    ),
    (
        "auditor",
        "Read-only access to the full traceability record, including audit logs.",
        "miguel.santos@demo.local",
        "Miguel Santos",
    ),
]


@register_generator
def generate_demo_users(context: SeedContext) -> None:
    # Import lazily so static seed metadata can be inspected without loading
    # the application's runtime settings and database engine.
    from app.core.password import hash_password

    session = context.session

    demo_password = os.getenv("SEED_DEMO_USER_PASSWORD")
    if not demo_password:
        raise RuntimeError(
            "Set SEED_DEMO_USER_PASSWORD before seeding demo users (see .env.example). "
            "It is hashed with app.core.security.hash_password before storage — this check "
            "only guards against an operator forgetting to configure a demo login at all."
        )
    demo_password_hash = hash_password(demo_password)

    users_by_role: dict[str, User] = {}
    for role_code, _description, email, display_name in ROLE_DEFINITIONS:
        role = session.execute(select(Role).where(Role.name == role_code)).scalar_one_or_none()
        if role is None:
            raise RuntimeError(
                f"Role {role_code!r} not found — expected migration 0001 to have seeded it. "
                "Run `alembic upgrade head` before seeding demo users."
            )
        user = User(email=email, display_name=display_name, password_hash=demo_password_hash)
        user.roles.append(UserRole(role=role))
        session.add(user)
        users_by_role[role_code] = user

    session.flush()  # populate ids for F3.4's decision-history generator
    context.artifacts["users_by_role"] = users_by_role
