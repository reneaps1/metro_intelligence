"""F3.2 (MI-17): fictitious demo catalog — 3 product families, ~8 parts,
10-25 characteristics each (mixed types, bilateral/unilateral tolerances,
CC/SC/standard), one demo plant with 3 lines / 2 CMM + 1 scanner, and one
characteristic with a tolerance-change history (spec versioning demo).
Out of scope here: measurement series (F3.3)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import (
    Area,
    Cell,
    Characteristic,
    CharacteristicClassification,
    InspectionFrequency,
    InspectionPlan,
    Line,
    Machine,
    MeasurementProgram,
    Organization,
    PartNumber,
    ProductFamily,
    Site,
    Specification,
)

from seed.generators.base import SeedContext, register_generator

CHARACTERISTIC_TYPES = ["diameter", "position", "flatness", "profile"]

# type -> (nominal_min, nominal_max, tolerance_min, tolerance_max); flatness
# and profile are nominally-zero form/position characteristics.
TOLERANCE_RANGES: dict[str, tuple[float, float, float, float]] = {
    "diameter": (8.0, 60.0, 0.03, 0.08),
    "position": (5.0, 300.0, 0.05, 0.3),
    "flatness": (0.0, 0.0, 0.03, 0.15),
    "profile": (0.0, 0.0, 0.03, 0.1),
}

CHARACTERISTIC_LABELS = {
    "diameter": "Bore Diameter",
    "position": "Mounting Hole Position",
    "flatness": "Flatness",
    "profile": "Profile",
}

FAMILIES = [
    (
        "MI-DEMO-FAM-SUSP",
        "Suspension Components (Demo)",
        [
            ("MI-DEMO-1001", "Bracket Front Left (Demo)"),
            ("MI-DEMO-1002", "Bracket Front Right (Demo)"),
            ("MI-DEMO-1003", "Control Arm (Demo)"),
        ],
    ),
    (
        "MI-DEMO-FAM-BRAKE",
        "Braking Components (Demo)",
        [
            ("MI-DEMO-1004", "Brake Caliper Mount (Demo)"),
            ("MI-DEMO-1005", "Brake Disc Carrier (Demo)"),
            ("MI-DEMO-1006", "Brake Line Bracket (Demo)"),
        ],
    ),
    (
        "MI-DEMO-FAM-BODY",
        "Body Panels (Demo)",
        [
            ("MI-DEMO-1007", "Door Hinge Bracket (Demo)"),
            ("MI-DEMO-1008", "Fender Mounting Bracket (Demo)"),
        ],
    ),
]

CLASSIFICATIONS = [
    ("critical", "Critical (CC)"),
    ("significant", "Significant (SC)"),
    ("standard", "Standard"),
]

FREQUENCY_BY_CLASSIFICATION = {"critical": 1, "significant": 5, "standard": 10}

LINE_CODES = ["L1", "L2", "L3"]
MACHINES = [("CMM-01", "CMM"), ("CMM-02", "CMM"), ("SCAN-01", "scanner")]


def _build_org_hierarchy(session) -> tuple[list[Line], list[Machine]]:
    organization = Organization(code="MI-DEMO-ORG", name="OnKaizen Demo Manufacturing")
    site = Site(organization=organization, code="PLANT-NORTE", name="Plant Demo Norte", timezone="America/Monterrey")
    area = Area(site=site, code="AREA-1", name="Assembly Area 1 (Demo)")
    organization.sites.append(site)
    site.areas.append(area)

    lines: list[Line] = []
    machines: list[Machine] = []
    for line_code, (machine_code, machine_type) in zip(LINE_CODES, MACHINES):
        line = Line(code=line_code, name=f"Line {line_code} (Demo)")
        cell = Cell(code="C1", name=f"Cell C1 ({line_code})")
        machine = Machine(code=machine_code, name=f"{machine_code} (Demo)", machine_type=machine_type)
        cell.machines.append(machine)
        line.cells.append(cell)
        area.lines.append(line)
        lines.append(line)
        machines.append(machine)

    session.add(organization)
    return lines, machines


def _classification_plan(rng, count: int) -> list[str]:
    """At least one 'critical' per part (F3.2 acceptance criterion)."""
    codes = ["critical"] + list(
        rng.choice(["critical", "significant", "standard"], size=count - 1, p=[0.2, 0.35, 0.45])
    )
    rng.shuffle(codes)
    return [str(code) for code in codes]


@register_generator
def generate_catalog(context: SeedContext) -> None:
    session = context.session
    rng = context.rng

    lines, machines = _build_org_hierarchy(session)

    classifications = {code: CharacteristicClassification(code=code, name=name) for code, name in CLASSIFICATIONS}
    session.add_all(classifications.values())

    all_parts: list[PartNumber] = []
    all_characteristics: list[Characteristic] = []
    versioned_characteristic_done = False

    for family_code, family_name, parts in FAMILIES:
        family = ProductFamily(code=family_code, name=family_name)
        session.add(family)

        for part_code, part_name in parts:
            part = PartNumber(code=part_code, name=part_name)
            family.part_numbers.append(part)
            all_parts.append(part)

            characteristic_count = int(rng.integers(10, 26))
            classification_codes = _classification_plan(rng, characteristic_count)
            program_mapping: dict[str, str] = {}
            part_characteristics: list[Characteristic] = []

            for i in range(characteristic_count):
                balloon = str(i + 1)
                char_type = CHARACTERISTIC_TYPES[i % len(CHARACTERISTIC_TYPES)]
                nominal_min, nominal_max, tol_min, tol_max = TOLERANCE_RANGES[char_type]
                nominal = round(float(rng.uniform(nominal_min, nominal_max)), 3) if nominal_max > 0 else 0.0
                tolerance = round(float(rng.uniform(tol_min, tol_max)), 3)
                unilateral = char_type in ("flatness", "profile") and rng.random() < 0.6
                classification_code = classification_codes[i]

                characteristic = Characteristic(
                    balloon_number=balloon,
                    name=f"{CHARACTERISTIC_LABELS[char_type]} {i + 1}",
                    characteristic_type=char_type,
                    unit="mm",
                    classification=classifications[classification_code],
                )
                part.characteristics.append(characteristic)
                part_characteristics.append(characteristic)
                all_characteristics.append(characteristic)
                program_mapping[balloon] = f"COL_{balloon}"

                lower_tol = None if unilateral else -tolerance
                upper_tol = tolerance

                # One CC characteristic gets a tolerance-change history: an
                # older, tighter spec superseded by the current one (demo of
                # CLAUDE.md §6 spec versioning).
                if not versioned_characteristic_done and classification_code == "critical":
                    old_valid_to = datetime.now(timezone.utc) - timedelta(days=60)
                    characteristic.specifications.append(
                        Specification(
                            nominal=nominal,
                            lower_tol=None if unilateral else -tolerance * 0.6,
                            upper_tol=tolerance * 0.6,
                            unit="mm",
                            valid_from=old_valid_to - timedelta(days=180),
                            valid_to=old_valid_to,
                        )
                    )
                    versioned_characteristic_done = True

                characteristic.specifications.append(
                    Specification(nominal=nominal, lower_tol=lower_tol, upper_tol=upper_tol, unit="mm")
                )

            program = MeasurementProgram(name=f"{part_name} — CMM Program", output_mapping=program_mapping)
            part.measurement_programs.append(program)

            plan = InspectionPlan(name="Default plan")
            part.inspection_plans.append(plan)
            for characteristic, classification_code in zip(part_characteristics, classification_codes):
                plan.frequencies.append(
                    InspectionFrequency(
                        characteristic=characteristic,
                        frequency_type="every_nth_part",
                        frequency_value=FREQUENCY_BY_CLASSIFICATION[classification_code],
                        reason="Initial baseline frequency (seed).",
                    )
                )

    session.flush()  # populate IDs for downstream generators (F3.3/F3.4) reading context.artifacts
    context.artifacts["parts"] = all_parts
    context.artifacts["characteristics"] = all_characteristics
    context.artifacts["lines"] = lines
    context.artifacts["machines"] = machines
