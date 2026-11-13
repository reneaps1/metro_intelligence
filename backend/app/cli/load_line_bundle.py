"""Load a line bundle end to end in an unattended job (ADR-004).

    python -m app.cli.load_line_bundle

For platforms without an interactive shell (e.g. a scheduled job). Everything
customer-specific arrives at run time through environment variables, never
from the repo:

- ``LINE_BUNDLE_URL``: HTTPS URL of a zip holding one folder per station.
- ``LINE_INGEST_CONFIG_YAML``: the ingest config (see ``config.example.yaml``).
  Station ``folder`` values are the folder names inside the zip.
- ``LINE_SPECS_YAML``: the specification file (see ``specs.example.yaml``).

Steps: download the zip (size-capped), extract only the station CSV files
that sit directly in a configured station folder, purge demo data on the
first run only, import specifications, load, rebuild daily stats, print the
reconciliation. Every step is resumable, so a run that dies is simply run
again. A completed bundle writes one audit entry; later runs with the same
inputs exit at once.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import time
import unicodedata
import urllib.request
import zipfile
from pathlib import Path

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.ingest.config import IngestConfig, load_config
from app.ingest.loader import AUDIT_ACTION as FILE_AUDIT_ACTION
from app.services.audit_service import write_audit_log

AUDIT_ACTION = "line_bundle_loaded"
AUDIT_ACTOR = "cli:load_line_bundle"
DEFAULT_WORK_DIR = "/tmp/line-bundle"
DEFAULT_MAX_DOWNLOAD_BYTES = 2 * 1024**3
DEFAULT_MAX_EXTRACTED_BYTES = 8 * 1024**3
CHUNK = 1 << 20
# pg advisory lock key: one bundle load at a time per database.
ADVISORY_LOCK_KEY = 7_212_023_001
LOCK_POLL_SECONDS = 15


class BundleError(RuntimeError):
    """The bundle cannot be loaded as given."""


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def bundle_key(url: str, config_text: str, specs_text: str) -> str:
    """Identity of one bundle run: same inputs, same key."""
    return hashlib.sha256("\0".join((url, config_text, specs_text)).encode()).hexdigest()


def download(url: str, dest: Path, max_bytes: int) -> int:
    """Stream `url` to `dest`, refusing anything that is not HTTPS or is
    larger than `max_bytes`. Returns the size."""
    if not url.startswith("https://"):
        raise BundleError("LINE_BUNDLE_URL must be an https:// URL.")
    size = 0
    with urllib.request.urlopen(url, timeout=60) as response, dest.open("wb") as out:  # noqa: S310
        while chunk := response.read(CHUNK):
            size += len(chunk)
            if size > max_bytes:
                raise BundleError(f"Download exceeds {max_bytes:,} bytes.")
            out.write(chunk)
    if not zipfile.is_zipfile(dest):
        raise BundleError("The downloaded file is not a zip archive.")
    return size


def extract_station_files(zip_path: Path, config: IngestConfig, out_dir: Path, max_bytes: int) -> int:
    """Copy the `.csv` files that sit directly in a configured station folder
    to `out_dir/<folder>/<file>`. Sub-folders (archives, copies) and every
    other member are ignored; member paths are never used as output paths."""
    folders = {_nfc(station.folder): station.folder for station in config.stations}
    count = 0
    written = 0
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            parts = info.filename.replace("\\", "/").split("/")
            if info.is_dir() or len(parts) < 2 or not parts[-1].lower().endswith(".csv"):
                continue
            folder = folders.get(_nfc(parts[-2]))
            if folder is None:
                continue
            written += info.file_size
            if written > max_bytes:
                raise BundleError(f"Extracted station files exceed {max_bytes:,} bytes.")
            target_dir = out_dir / folder
            target_dir.mkdir(parents=True, exist_ok=True)
            name = Path(parts[-1]).name
            with archive.open(info) as src, (target_dir / name).open("wb") as dst:
                shutil.copyfileobj(src, dst, CHUNK)
            count += 1
    return count


def _already_loaded(engine: Engine, key: str) -> bool:
    with engine.connect() as conn:
        return (
            conn.execute(
                text(
                    "SELECT 1 FROM security_audit_log "
                    "WHERE action = :action AND after_state ->> 'bundle' = :key LIMIT 1"
                ),
                {"action": AUDIT_ACTION, "key": key},
            ).first()
            is not None
        )


def _files_ever_loaded(engine: Engine) -> bool:
    with engine.connect() as conn:
        return (
            conn.execute(
                text("SELECT 1 FROM security_audit_log WHERE action = :action LIMIT 1"),
                {"action": FILE_AUDIT_ACTION},
            ).first()
            is not None
        )


def _run(step: str, code: int) -> None:
    if code != 0:
        raise BundleError(f"Step {step} failed with exit code {code}.")


def main(argv: list[str] | None = None) -> int:
    del argv
    url = os.getenv("LINE_BUNDLE_URL", "").strip()
    config_text = os.getenv("LINE_INGEST_CONFIG_YAML", "")
    specs_text = os.getenv("LINE_SPECS_YAML", "")
    if not (url and config_text.strip() and specs_text.strip()):
        print(
            "Line bundle not configured "
            "(LINE_BUNDLE_URL, LINE_INGEST_CONFIG_YAML, LINE_SPECS_YAML); nothing to do."
        )
        return 0

    from app.core.database import engine

    key = bundle_key(url, config_text, specs_text)
    if _already_loaded(engine, key):
        print("This line bundle is already loaded; nothing to do.")
        return 0

    # During a deploy the old instance can still hold the lock for a while:
    # wait for it (LINE_BUNDLE_LOCK_WAIT_SECONDS) instead of giving up.
    wait = float(os.getenv("LINE_BUNDLE_LOCK_WAIT_SECONDS", "0") or 0)
    deadline = time.monotonic() + wait
    with engine.connect() as lock_conn:
        while True:
            locked = lock_conn.execute(
                text("SELECT pg_try_advisory_lock(:key)"), {"key": ADVISORY_LOCK_KEY}
            ).scalar_one()
            lock_conn.commit()  # session-level lock: no transaction stays open during the load
            if locked or time.monotonic() >= deadline:
                break
            time.sleep(min(LOCK_POLL_SECONDS, max(0.0, deadline - time.monotonic())))
        if not locked:
            print("Another line bundle load is running; nothing to do.")
            return 0
        try:
            return _load(engine, key, url, config_text, specs_text)
        finally:
            lock_conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": ADVISORY_LOCK_KEY})
            lock_conn.commit()


def _load(engine: Engine, key: str, url: str, config_text: str, specs_text: str) -> int:
    from app.cli import build_daily_stats, import_specifications, ingest_line, ingest_report
    from app.cli.purge_domain_data import purge

    if _already_loaded(engine, key):  # finished by another run while we waited
        print("This line bundle is already loaded; nothing to do.")
        return 0

    work = Path(os.getenv("LINE_BUNDLE_WORK_DIR", DEFAULT_WORK_DIR))
    data_dir = work / "data"
    work.mkdir(parents=True, exist_ok=True)
    config_path = work / "ingest.yaml"
    specs_path = work / "specs.yaml"
    config_path.write_text(config_text, encoding="utf-8")
    specs_path.write_text(specs_text, encoding="utf-8")
    config = load_config(config_path)

    try:
        zip_path = work / "bundle.zip"
        size = download(url, zip_path, int(os.getenv("LINE_BUNDLE_MAX_BYTES", DEFAULT_MAX_DOWNLOAD_BYTES)))
        print(f"Downloaded {size:,} bytes.", flush=True)
        files = extract_station_files(zip_path, config, data_dir, DEFAULT_MAX_EXTRACTED_BYTES)
        zip_path.unlink()
        print(f"Extracted {files:,} station files.", flush=True)
        if files == 0:
            raise BundleError("No station files found: check the station folder names in the config.")

        if not _files_ever_loaded(engine):
            counts = purge(engine)
            print(
                f"First load: purged {sum(counts.values()):,} demo rows (users and audit log kept).",
                flush=True,
            )

        common = ["--config", str(config_path)]
        _run(
            "import_specifications",
            import_specifications.main([*common, "--data-dir", str(data_dir), "--file", str(specs_path)]),
        )
        _run("ingest_line", ingest_line.main([*common, "--data-dir", str(data_dir), "--raw-store", "skip"]))
        _run("build_daily_stats", build_daily_stats.main(common))
        _run("ingest_report", ingest_report.main(common))

        with Session(engine) as session:
            write_audit_log(
                session,
                action=AUDIT_ACTION,
                entity_type="system",
                actor_identifier=AUDIT_ACTOR,
                after_state={"bundle": key, "line": config.line.code, "station_files": files},
            )
            session.commit()
        print("Line bundle loaded.", flush=True)
        return 0
    except BundleError as exc:
        print(f"Line bundle failed: {exc}", file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
