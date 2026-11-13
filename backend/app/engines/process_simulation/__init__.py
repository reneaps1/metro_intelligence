"""IQ-F2: deterministic simulator of injection-moulding process signals.

Everything produced here is SIMULATED -- generic physics-flavoured profiles,
not measurements or specifications of any real plant or machine. See README.md.
"""

from app.engines.process_simulation.catalog import (
    MACHINES,
    SIGNALS,
    MachineDefinition,
    SignalDefinition,
    build_tree,
    parse_signal_id,
    signal_id,
)
from app.engines.process_simulation.generator import (
    GENERATOR_VERSION,
    SCENARIO_DURATION_S,
    SCENARIO_START,
    SeriesResult,
    build_timeline,
    evaluate,
    generate_series,
    scenario_events,
)
from app.engines.process_simulation.scenarios import SCENARIOS, Scenario, ScenarioEvent, get_scenario

__all__ = [
    "GENERATOR_VERSION",
    "MACHINES",
    "SCENARIOS",
    "SCENARIO_DURATION_S",
    "SCENARIO_START",
    "SIGNALS",
    "MachineDefinition",
    "Scenario",
    "ScenarioEvent",
    "SeriesResult",
    "SignalDefinition",
    "build_timeline",
    "build_tree",
    "evaluate",
    "generate_series",
    "get_scenario",
    "parse_signal_id",
    "scenario_events",
    "signal_id",
]
