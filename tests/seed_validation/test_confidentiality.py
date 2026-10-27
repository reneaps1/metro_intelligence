"""F3.5 (MI-20): confidentiality lint over the seed's own identifiers and
generated sample files (CLAUDE.md §7/§11/§20 -- the project's release
blocker). Needs no database: it lints the generators' static constants and
the checked-in seed/sample_files/* content directly, so it stays fast
(<2 min acceptance criterion, docs/tasks/F3.5.md) and runnable without a
Postgres instance.

Includes a "test of the test" (F3.5's own testing note): deliberately
planted real-shaped identifiers that must be caught, so a silently broken
lint can't pass CI by accident.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
for path in (REPO_ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from openpyxl import load_workbook  # noqa: E402

from seed.generators.catalog import FAMILIES, LINE_CODES, MACHINES  # noqa: E402
from seed.generators.users import ROLE_DEFINITIONS  # noqa: E402
from seed.validation.confidentiality import (  # noqa: E402
    DEFAULT_PRIVATE_TERMS_FILE,
    PRIVATE_TERMS_ENV,
    check_email,
    check_identifier,
    load_private_terms,
    scan_files,
)

SAMPLE_FILES_DIR = REPO_ROOT / "seed" / "sample_files"

# Identifier-shaped columns worth linting in the sample files (measurement
# value columns are numbers, not identifiers -- nothing to lint there).
SAMPLE_FILE_IDENTIFIER_COLUMNS = {"part_number", "batch_lot", "machine_code", "operator_identifier"}


def _catalog_identifiers() -> list[str]:
    identifiers: list[str] = ["Plant Demo Norte", "MI-DEMO-ORG", "Assembly Area 1 (Demo)"]
    for family_code, family_name, parts in FAMILIES:
        identifiers.append(family_code)
        identifiers.append(family_name)
        for part_code, part_name in parts:
            identifiers.append(part_code)
            identifiers.append(part_name)
    identifiers.extend(LINE_CODES)
    for machine_code, _machine_type in MACHINES:
        identifiers.append(machine_code)
    return identifiers


def test_lint_accepts_every_catalog_identifier() -> None:
    for identifier in _catalog_identifiers():
        assert check_identifier(identifier) == [], f"false positive on fictitious identifier {identifier!r}"


def test_lint_accepts_every_seed_user_email() -> None:
    emails = [email for _role, _description, email, _display_name in ROLE_DEFINITIONS]
    assert emails, "expected at least one seed user email to check"
    for email in emails:
        assert check_email(email) == [], f"false positive on fictitious email {email!r}"


def test_lint_accepts_generated_csv_sample_files() -> None:
    csv_files = sorted(SAMPLE_FILES_DIR.glob("*.csv"))
    assert csv_files, "expected seed/sample_files/*.csv to exist (run seed/scripts/generate_sample_files.py)"

    for csv_path in csv_files:
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                for column in SAMPLE_FILE_IDENTIFIER_COLUMNS & set(row):
                    value = row[column]
                    assert check_identifier(value) == [], (
                        f"false positive in {csv_path.name}, column {column!r}: {value!r}"
                    )


def test_lint_accepts_generated_xlsx_sample_file() -> None:
    xlsx_files = sorted(SAMPLE_FILES_DIR.glob("*.xlsx"))
    assert xlsx_files, "expected seed/sample_files/*.xlsx to exist (run seed/scripts/generate_sample_files.py)"

    for xlsx_path in xlsx_files:
        workbook = load_workbook(xlsx_path, read_only=True)
        try:
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                rows = sheet.iter_rows(values_only=True)
                header = [str(cell) for cell in next(rows)]
                identifier_indexes = [
                    index for index, column in enumerate(header) if column in SAMPLE_FILE_IDENTIFIER_COLUMNS
                ]
                for row in rows:
                    for index in identifier_indexes:
                        value = str(row[index])
                        assert check_identifier(value) == [], (
                            f"false positive in {xlsx_path.name}/{sheet_name}, column {header[index]!r}: {value!r}"
                        )
        finally:
            workbook.close()


def test_lint_catches_bmw_style_grouped_part_number() -> None:
    # Structural shape of a real 11-digit BMW part number (2-2-1-3-3 grouping)
    # -- not a real number, just its shape -- must never slip through as a
    # fictitious MI-DEMO-* identifier.
    violations = check_identifier("51 11 7 123 456")
    assert violations, "lint failed to catch a BMW-shaped part number"


def test_lint_catches_vag_style_grouped_part_number() -> None:
    # Structural shape of a VW/Audi/Porsche/Skoda/Seat part number.
    violations = check_identifier("8E0-123-456-A")
    assert violations, "lint failed to catch a VAG-shaped part number"


def test_lint_catches_generic_long_digit_run() -> None:
    violations = check_identifier("123456789")
    assert violations, "lint failed to catch a generic long numeric identifier"


def test_lint_catches_real_oem_name_token() -> None:
    for planted in ["BMW Bracket Front Left", "Mercedes-Benz Caliper", "supplied by Bosch"]:
        violations = check_identifier(planted)
        assert violations, f"lint failed to catch a real OEM name token in {planted!r}"


def test_lint_catches_real_oem_plant_token() -> None:
    for planted in ["Plant Munich", "Werk Dingolfing Halle 3", "Spartanburg Line 2"]:
        violations = check_identifier(planted)
        assert violations, f"lint failed to catch a real OEM plant name in {planted!r}"


def test_lint_catches_non_local_email_domain() -> None:
    for planted in ["ana.garcia@bmw.com", "quality@onkaizen-demo.io", "test@gmail.com"]:
        violations = check_email(planted)
        assert violations, f"lint failed to catch a non-.local email in {planted!r}"


def test_lint_does_not_flag_fictitious_mi_demo_prefix_even_if_digit_heavy() -> None:
    # MI-DEMO-* is this project's own scheme (docs/seed-data-strategy.md) and
    # must stay exempt from the part-number shape checks that would
    # otherwise flag its digit suffix.
    assert check_identifier("MI-DEMO-1001") == []


# --------------------------------------------------------------------------- #
# IQ-F8: industrial-demo fixtures and the private deny-list scan
# --------------------------------------------------------------------------- #

DIMENSIONAL_IDENTIFIER_COLUMNS = {"ID_Pieza", "Nido", "Maquina", "serial", "cavity", "press", "material_lot"}


def test_lint_accepts_dimensional_sample_identifiers() -> None:
    files = sorted(SAMPLE_FILES_DIR.glob("mi_demo_dimensional_*.csv"))
    assert len(files) == 2, "expected the IQ-F6 long and wide dimensional samples"
    for csv_path in files:
        text = csv_path.read_text(encoding="utf-8")
        dialect = csv.Sniffer().sniff(text.splitlines()[0], delimiters=",;")
        reader = csv.DictReader(text.splitlines(), dialect=dialect)
        columns = DIMENSIONAL_IDENTIFIER_COLUMNS & set(reader.fieldnames or [])
        assert columns, f"no identifier columns recognised in {csv_path.name}"
        for row in reader:
            for column in columns:
                assert check_identifier(row[column]) == [], f"{csv_path.name}, {column!r}: {row[column]!r}"


def _tracked_files() -> list[str]:
    import subprocess

    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO_ROOT, capture_output=True, check=True
    ).stdout.decode("utf-8")
    return [str(REPO_ROOT / name) for name in out.split("\0") if name]


def test_no_private_term_in_any_tracked_file() -> None:
    import os

    import pytest

    path = os.getenv(PRIVATE_TERMS_ENV) or str(REPO_ROOT / DEFAULT_PRIVATE_TERMS_FILE)
    terms = load_private_terms(path)
    if not terms:
        pytest.skip("no private deny-list available (expected in CI); see seed/validation/confidentiality.py")
    hits = scan_files(_tracked_files(), terms)
    # Report paths only: echoing the matched term would print the secret itself.
    assert not hits, f"private terms found in tracked files: {sorted({p for p, _ in hits})}"


def test_private_scan_catches_a_planted_term(tmp_path: Path) -> None:
    terms_file = tmp_path / "terms.txt"
    terms_file.write_text("# comment\nAcmeTestCo\nab\n", encoding="utf-8")
    terms = load_private_terms(str(terms_file))
    assert terms == ["AcmeTestCo"], "comments and too-short terms must be ignored"
    leaky = tmp_path / "notes.md"
    leaky.write_text("Demo para ACMETESTCO, planta norte", encoding="utf-8")
    clean = tmp_path / "clean.md"
    clean.write_text("Cliente demo", encoding="utf-8")
    binary = tmp_path / "blob.bin"
    binary.write_bytes(b"\x00AcmeTestCo")
    assert scan_files([str(leaky), str(clean), str(binary)], terms) == [(str(leaky), "AcmeTestCo")]
    assert load_private_terms(str(tmp_path / "missing.txt")) == []
