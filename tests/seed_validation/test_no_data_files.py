"""IQ-F21 (plan decision D15): no raw export, converted dataset or camera image is ever tracked.

Real customer data must never enter the repository (CLAUDE.md §7, §16; plan
decision D8). `.gitignore` already ignores these extensions; this test catches
a forced ``git add -f`` or a renamed rule. Fictitious twin datasets shipped
with the app (plan phase F26) must be added to ``ALLOWED`` one exact path at a
time, never by pattern.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BANNED_SUFFIXES = (".zip", ".csv.gz", ".bmp", ".parquet", ".7z", ".rar", ".tar", ".tgz")
ALLOWED: frozenset[str] = frozenset()


def _tracked_files() -> list[str]:
    git = shutil.which("git")
    if git is None or not (REPO_ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    out = subprocess.run(
        [git, "ls-files", "-z"], cwd=REPO_ROOT, check=True, capture_output=True
    ).stdout.decode("utf-8")
    return [f for f in out.split("\0") if f]


def test_no_data_archives_or_images_are_tracked() -> None:
    offending = [
        f for f in _tracked_files() if f.lower().endswith(BANNED_SUFFIXES) and f not in ALLOWED
    ]
    assert offending == [], f"data files must not be tracked: {offending}"


def test_private_folders_are_ignored() -> None:
    ignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    for rule in ("demo-private/", "*.zip", "*.csv.gz", "*.bmp"):
        assert rule in ignore, rule
