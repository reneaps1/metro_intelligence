"""F3.4 (MI-19): one demo user per RBAC role (docs/security/rbac.md), all on
the deliberately artificial `.local` domain (docs/seed-data-strategy.md).
Password hashing is F4.2's job, not implemented yet — SEED_DEMO_USER_PASSWORD
only exists so seeding fails loudly if nobody has set an intended demo
password (CLAUDE.md §5: no hardcoded credentials), not so this generator can
roll its own hashing. Until F4.2 lands, password_hash stays None rather than
storing an ad-hoc/placeholder hash."""
from __future__ import annotations

import os

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
    session = context.session

    if not os.getenv("SEED_DEMO_USER_PASSWORD"):
        raise RuntimeError(
            "Set SEED_DEMO_USER_PASSWORD before seeding demo users (see .env.example). "
            "Hashing it into password_hash is F4.2's responsibility — this check only "
            "guards against an operator forgetting to configure a demo login at all."
        )

    users_by_role: dict[str, User] = {}
    for role_code, description, email, display_name in ROLE_DEFINITIONS:
        role = Role(name=role_code, description=description, is_system=True)
        user = User(email=email, display_name=display_name, password_hash=None)
        user.roles.append(UserRole(role=role))
        session.add_all([role, user])
        users_by_role[role_code] = user

    session.flush()  # populate ids for F3.4's decision-history generator
    context.artifacts["users_by_role"] = users_by_role
