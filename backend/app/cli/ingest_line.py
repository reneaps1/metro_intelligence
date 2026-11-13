"""Load a line's station exports into the process model (ADR-004/005).

    python -m app.cli.ingest_line --config ingest.yaml --data-dir /data/line --dry-run
    python -m app.cli.ingest_line --config ingest.yaml --data-dir /data/line

Resumable: files already loaded (same SHA-256) are skipped. Run
`import_specifications` before the first load so results carry their
compliance verdict, and `build_daily_stats` after it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from app.cli._line import add_config_argument, add_data_dir_argument, config_from_args, earliest_data_day
from app.ingest.loader import LineLoader, LoadSummary
from app.ingest.setup import ensure_catalog

COLUMNS = (
    ("files", "files"),
    ("files_skipped", "skipped"),
    ("rows_read", "read"),
    ("rows_loaded", "loaded"),
    ("values_loaded", "values"),
    ("excluded_recipe", "other recipe"),
    ("excluded_program", "other program"),
    ("scope_unknown", "scope unknown"),
    ("quarantined", "quarantined"),
    ("repeat_attempts", "repeats"),
    ("pieces_without_recipe", "no recipe"),
)


def print_summary(summary: LoadSummary) -> None:
    totals = summary.totals_by_station()
    print("station    " + "".join(f"{label:>15}" for _key, label in COLUMNS))
    for station, counter in totals.items():
        print(f"{station:<11}" + "".join(f"{counter[key]:>15,}" for key, _label in COLUMNS))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_config_argument(parser)
    add_data_dir_argument(parser)
    parser.add_argument("--dry-run", action="store_true", help="Parse and count without writing anything.")
    parser.add_argument("--station", action="append", help="Only this station code (repeatable).")
    parser.add_argument("--limit-files", type=int, help="At most this many files per station (smoke runs).")
    parser.add_argument(
        "--raw-store",
        choices=("minio", "skip"),
        default="minio",
        help="Keep each raw file in object storage (default) or skip it (local trials only).",
    )
    args = parser.parse_args(argv)
    config = config_from_args(parser, args)
    if args.data_dir is None or not Path(args.data_dir).is_dir():
        parser.error("--data-dir or LINE_DATA_DIR must point to the station folders.")

    from app.core.database import engine

    with Session(engine) as session:
        catalog = ensure_catalog(session, config, earliest_data_day(config, args.data_dir))
        if args.dry_run:
            session.rollback()
        else:
            session.commit()

    storage = None
    bucket = ""
    if not args.dry_run and args.raw_store == "minio":
        from app.core.config import get_settings
        from app.services.storage_service import get_object_storage

        storage = get_object_storage()
        bucket = get_settings().minio_bucket_raw_files

    loader = LineLoader(engine, config, catalog, Path(args.data_dir), storage, bucket, progress=print)
    pieces = loader.scan_recipes()
    print(f"Type check: {pieces:,} piece ids with a recipe.")
    if not args.dry_run:
        loader.load_state()
    summary = loader.load(args.station, args.limit_files, dry_run=args.dry_run)
    print_summary(summary)
    if args.dry_run:
        print("Dry run: nothing was written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
