"""Reconcile what was loaded for a line with what the station files held.

    python -m app.cli.ingest_report --config ingest.yaml

Per station, from the audit entry each loaded file wrote:
rows read = loaded + other recipe + other program + scope unknown + quarantined.
Then the stored pieces per recipe and rows per table.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter

from sqlalchemy import text

from app.cli._line import add_config_argument, config_from_args
from app.ingest.loader import AUDIT_ACTION

ACCOUNTED = ("rows_loaded", "excluded_recipe", "excluded_program", "scope_unknown", "quarantined")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_config_argument(parser)
    args = parser.parse_args(argv)
    config = config_from_args(parser, args)

    from app.core.database import engine

    totals: dict[str, Counter[str]] = {}
    with engine.connect() as conn:
        for (state,) in conn.execute(
            text("SELECT after_state FROM security_audit_log WHERE action = :action"),
            {"action": AUDIT_ACTION},
        ):
            counter = totals.setdefault(state["station"], Counter())
            counter["files"] += 1
            for key, value in state.items():
                if isinstance(value, int) and not isinstance(value, bool):
                    counter[key] += value

        print("station       files        read      loaded    excluded   quarantined   balanced")
        for station in config.stations:
            c = totals.get(station.code, Counter())
            excluded = c["excluded_recipe"] + c["excluded_program"] + c["scope_unknown"]
            balanced = c["rows_read"] == sum(c[key] for key in ACCOUNTED)
            print(
                f"{station.code:<11}{c['files']:>8,}{c['rows_read']:>12,}{c['rows_loaded']:>12,}"
                f"{excluded:>12,}{c['quarantined']:>14,}{'yes' if balanced else 'NO':>11}"
            )

        print("\nPieces by recipe")
        for code, label, pieces in conn.execute(
            text(
                "SELECT r.code, r.variant_label, count(pi.id) FROM process_part_instances pi "
                "LEFT JOIN process_recipes r ON r.id = pi.recipe_id "
                "JOIN org_lines l ON l.id = pi.line_id WHERE l.code = :line "
                "GROUP BY r.code, r.variant_label ORDER BY r.code NULLS LAST"
            ),
            {"line": config.line.code},
        ):
            name = f"Recipe {code}" if code is not None else "No recipe (not seen at type check)"
            print(f"  {name:<36}{label or 'variant pending':<24}{pieces:>12,}")

        print("\nRows stored")
        for table in (
            "process_step_results",
            "measurement_results",
            "measurement_quarantined_rows",
            "process_step_daily",
            "process_characteristic_daily",
        ):
            count = conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            print(f"  {table:<36}{count:>16,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
