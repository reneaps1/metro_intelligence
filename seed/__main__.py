"""Deterministic demo-data seed CLI.

Usage:
    python -m seed --reset --scenario stable_capable

F3.1 ships the framework only: config loading, a seeded RNG, DB reset, and a
generator-registration hook. F3.2-F3.4 register the generators that actually
populate the catalog, measurement series, process events, users, and
recommendation history — until then, --scenario just validates the name and
--reset wipes the database.
"""
from __future__ import annotations

import argparse
import sys

from seed.config import load_config
from seed.db import get_engine, get_session, reset_database
from seed.generators import SeedContext, make_rng, registered_generators


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m seed", description=__doc__)
    parser.add_argument("--reset", action="store_true", help="Truncate all tables before seeding.")
    parser.add_argument("--scenario", default=None, help="Scenario name from seed/config/scenarios.yaml.")
    parser.add_argument("--seed", type=int, default=None, help="Override the RNG seed (default: config's default_seed).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    config = load_config()

    if args.scenario is not None:
        config.scenario(args.scenario)  # raises ValueError with the valid list if unknown

    seed_value = args.seed if args.seed is not None else config.settings.default_seed
    rng = make_rng(seed_value)

    engine = get_engine()
    if args.reset:
        print("Resetting database (TRUNCATE ... CASCADE)...")
        reset_database(engine)

    generators = registered_generators()
    if not generators:
        print(
            "No dataset generators registered yet (F3.2-F3.4 land those). "
            "Framework check: config loaded, RNG seeded, DB reset ran if requested."
        )
        return 0

    session = get_session(engine)
    context = SeedContext(session=session, rng=rng, config=config)
    try:
        for generator in generators:
            generator(context)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
