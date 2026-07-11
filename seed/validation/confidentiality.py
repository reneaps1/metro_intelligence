"""F3.5 (MI-20): confidentiality lint — CLAUDE.md §7/§11/§20's release blocker.

Rejects anything in generated demo data that could be mistaken for a real
customer identifier: real OEM/Tier-1 name tokens, part-number strings shaped
like a known OEM numbering scheme, real plant/city names, and any email
outside the fictitious `.local` domain.

Deliberately pattern/structure-based rather than a copied list of real part
numbers: CLAUDE.md forbids putting real-looking (or real) customer
identifiers in this repo, so the lint itself must not smuggle any in — it
recognizes the *shape* of known numbering schemes instead.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

DEMO_PART_NUMBER_PREFIX = "MI-DEMO-"
DEMO_EMAIL_SUFFIX = "@demo.local"

# Real OEM / Tier-1 supplier names. Case-insensitive substring match — a
# fictitious identifier should never need to mention a real manufacturer.
KNOWN_OEM_NAME_TOKENS = [
    "bmw",
    "mini",
    "rolls-royce",
    "mercedes",
    "daimler",
    "audi",
    "volkswagen",
    "porsche",
    "skoda",
    "seat",
    "stellantis",
    "opel",
    "ford",
    "general motors",
    "toyota",
    "honda",
    "nissan",
    "volvo",
    "bosch",
    "continental",
    "zf friedrichshafen",
    "magna",
    "denso",
]

# Real plant/manufacturing-site cities associated with major automotive OEMs.
# "Plant Demo Norte" / "Plant Demo Sur" etc. never collide with these.
KNOWN_OEM_PLANT_TOKENS = [
    "munich",
    "münchen",
    "dingolfing",
    "regensburg",
    "leipzig",
    "spartanburg",
    "wolfsburg",
    "ingolstadt",
    "zuffenhausen",
    "sindelfingen",
    "bremen",
    "rastatt",
    "san luis potosi",
    "san luis potosí",
    "puebla",
    "silao",
    "toluca",
    "saltillo",
    "ramos arizpe",
    "aguascalientes",
]

# Structural shapes real OEM part numbers commonly take. These match
# *patterns*, not literal numbers, so this module never has to contain (and
# thus never risks leaking) an actual real part number.
OEM_PART_NUMBER_PATTERNS = [
    # BMW-style 11-digit grouped number, e.g. "51 11 7 123 456" or with dashes.
    re.compile(r"\b\d{2}[\s-]?\d{2}[\s-]?\d{1}[\s-]?\d{3}[\s-]?\d{3}\b"),
    # VAG-style (VW/Audi/Porsche/Skoda/Seat) grouped alphanumeric number,
    # e.g. "8E0-123-456-A" / "1K0 123 456 B".
    re.compile(r"\b[0-9][A-Z0-9]{2}[\s-]\d{3}[\s-]\d{3}(?:[\s-][A-Z])?\b"),
    # Generic long digit-only run (9-11 digits, no letters/prefix) typical of
    # OEM/ERP part master numbers with no separators.
    re.compile(r"(?<![A-Z0-9-])\d{9,11}(?![A-Z0-9-])"),
]


@dataclass(frozen=True)
class Violation:
    value: str
    reason: str

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return f"{self.value!r}: {self.reason}"


def _contains_known_token(text: str, tokens: list[str]) -> str | None:
    lowered = text.lower()
    for token in tokens:
        if token in lowered:
            return token
    return None


def check_identifier(value: str) -> list[Violation]:
    """Lints a single identifier/name string (part number, plant name, line
    name, machine name, product family name, free-text description...).
    Anything starting with the fictitious `MI-DEMO-` prefix is exempt from
    the part-number shape checks (it's the one scheme this project owns),
    but OEM name/plant tokens are still rejected everywhere — a demo
    identifier must never namedrop a real manufacturer either."""
    violations: list[Violation] = []

    if oem_name := _contains_known_token(value, KNOWN_OEM_NAME_TOKENS):
        violations.append(Violation(value, f"contains a known real OEM/supplier name token ({oem_name!r})"))

    if oem_plant := _contains_known_token(value, KNOWN_OEM_PLANT_TOKENS):
        violations.append(Violation(value, f"contains a known real OEM plant/city name token ({oem_plant!r})"))

    if not value.startswith(DEMO_PART_NUMBER_PREFIX):
        for pattern in OEM_PART_NUMBER_PATTERNS:
            if pattern.search(value):
                violations.append(
                    Violation(value, f"matches a known OEM part-number shape ({pattern.pattern})")
                )
                break

    return violations


def check_email(value: str) -> list[Violation]:
    """Every demo user/contact email must be on the fictitious `.local`
    domain (docs/seed-data-strategy.md) — nothing that could resolve to a
    real mailbox."""
    if not value.endswith(DEMO_EMAIL_SUFFIX):
        return [Violation(value, f"email is not on the fictitious {DEMO_EMAIL_SUFFIX} domain")]
    return []


def lint_identifiers(values: list[str]) -> list[Violation]:
    violations: list[Violation] = []
    for value in values:
        violations.extend(check_identifier(value))
    return violations


def lint_emails(values: list[str]) -> list[Violation]:
    violations: list[Violation] = []
    for value in values:
        violations.extend(check_email(value))
    return violations
