"""Remove all domain data while keeping identities and the audit trail.

Domain data is everything the platform manages about plants, catalog,
measurements, process steps, context and intelligence. Identities (users,
roles, permissions and their links) and the append-only audit log are kept:
users keep their accounts and every past action stays traceable (ADR-004).

TRUNCATE bypasses the row-level immutability triggers on measurement and
decision tables by design: this is an explicit administrative reset, never an
application code path, and it is recorded in the audit log by the caller.
"""

from __future__ import annotations

from sqlalchemy import Connection, Table, func, select, text

PRESERVED_TABLE_PREFIX = "security_"


def domain_tables() -> list[Table]:
    """Every mapped table except the security ones, in dependency order."""
    from app.models import Base

    return [
        table for table in Base.metadata.sorted_tables if not table.name.startswith(PRESERVED_TABLE_PREFIX)
    ]


def count_domain_rows(connection: Connection) -> dict[str, int]:
    """Row count per domain table (partition parents count their children)."""
    return {
        table.name: int(connection.execute(select(func.count()).select_from(table)).scalar_one())
        for table in domain_tables()
    }


def truncate_domain_tables(connection: Connection) -> None:
    """Empty every domain table in one statement.

    No CASCADE: if a preserved table ever gains a foreign key into domain
    data, PostgreSQL refuses the TRUNCATE instead of silently wiping users.
    """
    names = ", ".join(f'"{table.name}"' for table in domain_tables())
    connection.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY"))
