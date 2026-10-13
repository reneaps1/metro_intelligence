"""Small, idempotent, fictional live-monitor dataset for Render demo only."""
import os
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import engine
from app.models import (
    Characteristic, CharacteristicClassification, MeasurementProgram,
    MeasurementResult, MeasurementRun, MeasurementSample, PartNumber,
    ProductFamily, Specification,
)

DEMO_FAMILY_CODE = "MI-LIVE-DEMO-2026"
PATTERNS = ("stable_capable", "slow_drift", "shift_after_event", "high_variance", "outlier_nok")


def load_demo_data_once():
    if os.getenv("LOAD_LIVE_DEMO_ONCE") != "1" or get_settings().app_env == "production":
        return
    rng = random.Random(20261013)
    with Session(engine) as session:
        # Transactional advisory lock protects against concurrent deploy starts.
        with session.begin():
            session.execute(text("SELECT pg_advisory_xact_lock(20261013, 801)"))
            exists = session.scalar(select(ProductFamily.id).where(ProductFamily.code == DEMO_FAMILY_CODE))
            if exists:
                print("LIVE_DEMO: already loaded, skipping", flush=True)
                return

            classification = session.scalar(
                select(CharacteristicClassification).where(CharacteristicClassification.code == "standard")
            )
            if classification is None:
                classification = CharacteristicClassification(code="standard", name="Standard")
                session.add(classification)
            family = ProductFamily(code=DEMO_FAMILY_CODE, name="Live Monitor - Fictional Demo")
            part = PartNumber(code="MI-LIVE-DEMO-P001", name="Demo Bracket - Fictional")
            family.part_numbers.append(part)
            session.add(family)
            program = MeasurementProgram(name="CMM Demo Replay", version=1, output_mapping={
                str(i): f"COL_{i}" for i in range(1, 6)
            })
            part.measurement_programs.append(program)
            chars = []
            for i, pattern in enumerate(PATTERNS, start=1):
                characteristic = Characteristic(
                    balloon_number=str(i), name=pattern.replace("_", " ").title(),
                    characteristic_type="diameter", unit="mm", classification=classification,
                )
                characteristic.specifications.append(
                    Specification(nominal=Decimal("20.000"), lower_tol=Decimal("-0.100"),
                                  upper_tol=Decimal("0.100"), unit="mm")
                )
                part.characteristics.append(characteristic)
                chars.append(characteristic)
            session.flush()

            now = datetime.now(timezone.utc)
            count = 0
            for day in range(75):
                measured_at = now - timedelta(days=75-day)
                run = MeasurementRun(
                    measurement_program_id=program.id, run_at=measured_at,
                    operator_identifier="FICTIONAL-DEMO",
                    batch_lot=f"LIVE-DEMO-{day:03d}",
                )
                session.add(run)
                for seq in range(1, 4):
                    sample = MeasurementSample(sample_sequence=seq)
                    run.samples.append(sample)
                session.flush()
                for sample in run.samples:
                    for index, characteristic in enumerate(chars):
                        if index == 0: deviation = rng.gauss(0, 0.012)
                        elif index == 1: deviation = 0.0013 * day + rng.gauss(0, 0.010)
                        elif index == 2: deviation = (0.075 if day >= 38 else 0) + rng.gauss(0, 0.012)
                        elif index == 3: deviation = rng.gauss(0, 0.052)
                        else: deviation = (0.16 if rng.random() < 0.08 else rng.gauss(0, 0.015))
                        spec = characteristic.specifications[0]
                        session.add(MeasurementResult(
                            measured_at=measured_at + timedelta(minutes=sample.sample_sequence),
                            measurement_sample_id=sample.id,
                            characteristic_id=characteristic.id,
                            specification_id=spec.id,
                            value=Decimal(str(round(20.0 + deviation, 6))),
                            deviation=Decimal(str(round(deviation, 6))),
                            is_ok=(-0.1 <= deviation <= 0.1),
                        ))
                        count += 1
            print(f"LIVE_DEMO: staging {len(chars)} characteristics and {count} measurements", flush=True)
        print("LIVE_DEMO: transaction committed; existing users untouched", flush=True)


if __name__ == "__main__":
    load_demo_data_once()
