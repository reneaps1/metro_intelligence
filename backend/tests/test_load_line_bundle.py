"""Unattended line bundle load (app/cli/load_line_bundle.py), synthetic data only."""

from __future__ import annotations

import os
import shutil
import zipfile
from pathlib import Path

import pytest

alembic_command = pytest.importorskip("alembic.command")
alembic_config = pytest.importorskip("alembic.config")
sa = pytest.importorskip("sqlalchemy")
yaml = pytest.importorskip("yaml")

from app.cli import load_line_bundle  # noqa: E402
from app.ingest.config import parse_config  # noqa: E402
from app.services.domain_purge import truncate_domain_tables  # noqa: E402

from line_csv_factory import LineFiles, Piece, config_dict  # noqa: E402

TEST_DATABASE_URL = os.getenv("METRO_TEST_DATABASE_URL")
BACKEND_DIR = Path(__file__).resolve().parents[1]
DAY = "2026-03-02"
# A station folder name with non-ASCII characters, as station PCs export them.
TYPE_FOLDER = "07_Typprüfung"
SPECS = {
    "source": "MI-DEMO drawing rev A",
    "valid_from": "2025-01-01T00:00:00Z",
    "specifications": [
        {"station": "LEN-CON", "measure": "pin", "nominal": 5.5, "lower_tol": -0.3, "upper_tol": 0.3},
    ],
}


def _bundle(tmp_path: Path) -> tuple[Path, dict]:
    """Zip the synthetic station files under a root folder, with an archive
    sub-folder and a non-CSV file that must both be ignored."""
    files = tmp_path / "files"
    LineFiles(day=DAY, pieces=[Piece("100001", recipe=2, nest=1, second=10)]).write(files)
    raw = config_dict()
    for station in raw["stations"]:
        if station["folder"] == "07_type":
            station["folder"] = TYPE_FOLDER
    zip_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        for path in sorted(files.rglob("*.csv")):
            folder = TYPE_FOLDER if path.parent.name == "07_type" else path.parent.name
            archive.write(path, f"line/{folder}/{path.name}")
            archive.write(path, f"line/{folder}/_Archiv/{path.name}")
        archive.writestr("line/07_type/readme.txt", "not a station file")
    return zip_path, raw


def test_extract_keeps_only_files_directly_in_station_folders(tmp_path):
    zip_path, raw = _bundle(tmp_path)
    config = parse_config(raw)
    out = tmp_path / "out"

    count = load_line_bundle.extract_station_files(zip_path, config, out, max_bytes=10**8)

    station_dirs = {p.name for p in out.iterdir()}
    assert TYPE_FOLDER in station_dirs
    assert not list(out.rglob("_Archiv"))
    assert count == len(list(out.rglob("*.csv")))
    with pytest.raises(load_line_bundle.BundleError):
        load_line_bundle.extract_station_files(zip_path, config, tmp_path / "small", max_bytes=10)


def test_download_refuses_plain_http(tmp_path):
    with pytest.raises(load_line_bundle.BundleError):
        load_line_bundle.download("http://example.invalid/x.zip", tmp_path / "x.zip", 10)


def test_unconfigured_job_does_nothing(monkeypatch):
    for key in ("LINE_BUNDLE_URL", "LINE_INGEST_CONFIG_YAML", "LINE_SPECS_YAML"):
        monkeypatch.delenv(key, raising=False)
    assert load_line_bundle.main([]) == 0


@pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="Set METRO_TEST_DATABASE_URL to a disposable PostgreSQL database."
)
def test_full_run_loads_once_and_then_skips(tmp_path, monkeypatch):
    cfg = alembic_config.Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    alembic_command.upgrade(cfg, "head")
    engine = sa.create_engine(TEST_DATABASE_URL)
    with engine.begin() as conn:
        truncate_domain_tables(conn)

    zip_path, raw = _bundle(tmp_path)
    downloads = []

    def fake_download(url, dest, max_bytes):
        downloads.append(url)
        shutil.copyfile(zip_path, dest)
        return dest.stat().st_size

    monkeypatch.setattr(load_line_bundle, "download", fake_download)
    # The commands use the app engine; point it at this test's database.
    monkeypatch.setattr("app.core.database.engine", engine)
    monkeypatch.setenv("LINE_BUNDLE_URL", "https://example.invalid/bundle.zip")
    monkeypatch.setenv("LINE_INGEST_CONFIG_YAML", yaml.safe_dump(raw, allow_unicode=True))
    monkeypatch.setenv("LINE_SPECS_YAML", yaml.safe_dump(SPECS))
    monkeypatch.setenv("LINE_BUNDLE_WORK_DIR", str(tmp_path / "work"))

    try:
        assert load_line_bundle.main([]) == 0
        with engine.connect() as conn:
            pieces = conn.execute(sa.text("SELECT count(*) FROM process_part_instances")).scalar_one()
            daily = conn.execute(sa.text("SELECT count(*) FROM process_step_daily")).scalar_one()
            markers = conn.execute(
                sa.text("SELECT count(*) FROM security_audit_log WHERE action = 'line_bundle_loaded'")
            ).scalar_one()
        assert pieces == 1
        assert daily > 0
        assert markers == 1
        assert not (tmp_path / "work").exists()

        # Same inputs again: exits before downloading anything.
        assert load_line_bundle.main([]) == 0
        assert len(downloads) == 1
    finally:
        with engine.begin() as conn:
            truncate_domain_tables(conn)
        engine.dispose()
        alembic_command.downgrade(cfg, "base")
