"""Import versioned specifications for a line (ADR-005).

    python -m app.cli.import_specifications --config ingest.yaml --file specs.yaml

The specification file stays outside the repo (ADR-004); see
`app/ingest/specs.example.yaml`. Rebuild the daily statistics afterwards so
the views reflect the new version.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from app.cli._line import add_config_argument, add_data_dir_argument, config_from_args, earliest_data_day
from app.ingest.setup import ensure_catalog
from app.ingest.specs import import_specifications, load_spec_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_config_argument(parser)
    add_data_dir_argument(parser)
    parser.add_argument("--file", type=Path, required=True, help="Specification YAML.")
    args = parser.parse_args(argv)
    config = config_from_args(parser, args)
    spec_file = load_spec_file(args.file)

    from app.core.database import engine

    with Session(engine) as session:
        catalog = ensure_catalog(session, config, earliest_data_day(config, args.data_dir))
        created = import_specifications(session, config, catalog, spec_file)
        session.commit()
    print(f"{len(created)} specification versions created from {spec_file.source!r}.")
    print("Run `python -m app.cli.build_daily_stats` to refresh the process views.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
