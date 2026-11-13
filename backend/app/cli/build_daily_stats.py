"""Rebuild a line's daily per-step statistics (ADR-005).

    python -m app.cli.build_daily_stats --config ingest.yaml

Run after each load and after each specification import.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cli._line import add_config_argument, config_from_args
from app.ingest.stats import build_daily_stats
from app.models import Area, Line, Organization, Site


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_config_argument(parser)
    args = parser.parse_args(argv)
    config = config_from_args(parser, args)

    from app.core.database import engine

    with Session(engine) as session:
        line_id = session.execute(
            select(Line.id)
            .join(Area, Area.id == Line.area_id)
            .join(Site, Site.id == Area.site_id)
            .join(Organization, Organization.id == Site.organization_id)
            .where(
                Organization.code == config.organization.code,
                Site.code == config.site.code,
                Area.code == config.area.code,
                Line.code == config.line.code,
            )
        ).scalar_one_or_none()
    if line_id is None:
        print("The line in the config has not been loaded yet; run ingest_line first.", file=sys.stderr)
        return 1
    counts = build_daily_stats(engine, line_id, config.timezone.key)
    steps, values = counts["step_rows"], counts["characteristic_rows"]
    print(f"Daily statistics rebuilt: {steps:,} step rows, {values:,} value rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
