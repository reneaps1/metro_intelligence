"""Shared argument handling for the line ingest commands."""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

from app.ingest.config import IngestConfig, load_config
from app.ingest.stations import file_day, station_files


def add_config_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        type=Path,
        default=os.getenv("INGEST_CONFIG_PATH"),
        help="Ingest config YAML (outside the repo). Default: $INGEST_CONFIG_PATH.",
    )


def add_data_dir_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=os.getenv("LINE_DATA_DIR"),
        help="Folder holding one subfolder per station. Default: $LINE_DATA_DIR.",
    )


def config_from_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> IngestConfig:
    if args.config is None:
        parser.error("--config or INGEST_CONFIG_PATH is required.")
    return load_config(Path(args.config))


def earliest_data_day(config: IngestConfig, data_dir: Path | None) -> datetime:
    """First day with a station file; programs are valid from then. Falls
    back to 2000-01-01 when no data folder is given."""
    days = []
    if data_dir is not None:
        for station in config.stations:
            files = station_files(data_dir, station)
            if files and (day := file_day(files[0])):
                days.append(day)
    first = min(days) if days else "2000-01-01"
    return datetime.fromisoformat(first).replace(tzinfo=config.timezone)
