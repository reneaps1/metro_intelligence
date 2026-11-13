"""Remove all domain data, keeping users, roles, permissions and the audit log.

    python -m app.cli.purge_domain_data --dry-run   # show what would be removed
    python -m app.cli.purge_domain_data --confirm   # remove it

Take a `pg_dump` first: the purge cannot be undone. One audit entry records
the per-table row counts that were removed.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.services.audit_service import write_audit_log
from app.services.domain_purge import count_domain_rows, truncate_domain_tables

AUDIT_ACTION = "domain_data_purged"
AUDIT_ACTOR = "cli:purge_domain_data"


def purge(engine: Engine) -> dict[str, int]:
    """Truncate domain tables and record the removed counts. Returns them."""
    with engine.begin() as connection:
        counts = count_domain_rows(connection)
        truncate_domain_tables(connection)
        with Session(bind=connection) as session:
            write_audit_log(
                session,
                action=AUDIT_ACTION,
                entity_type="system",
                actor_identifier=AUDIT_ACTOR,
                before_state={"rows": counts},
                after_state={"rows": dict.fromkeys(counts, 0)},
            )
            session.flush()
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Print row counts without removing anything.")
    mode.add_argument("--confirm", action="store_true", help="Remove all domain data.")
    args = parser.parse_args(argv)

    from app.core.database import engine

    if args.dry_run:
        with engine.connect() as connection:
            counts = count_domain_rows(connection)
        verb = "Would remove"
    else:
        counts = purge(engine)
        verb = "Removed"

    for table, rows in counts.items():
        if rows:
            print(f"{verb} {rows:>12,} rows  {table}")
    print(
        f"{verb} {sum(counts.values()):,} rows in {sum(1 for r in counts.values() if r)} tables. "
        "Users, roles, permissions and the audit log are kept."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
