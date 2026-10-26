"""Versioned, reproducible process scenarios for the simulator.

Each scenario is pure data: piecewise deviations, windows and annotated
events, all as offsets (seconds) from the scenario start. Deviations apply to
the primary machine only. Nothing here is conditioned on real quality labels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

H = 3600.0

EventType = Literal[
    "batch_change",
    "tool_change",
    "alarm",
    "setpoint_change",
    "thermal_instability",
    "pressure_instability",
    "downtime",
    "intervention",
]
Severity = Literal["info", "warning", "critical"]


@dataclass(frozen=True)
class ScenarioEvent:
    offset_s: float
    duration_s: float | None
    event_type: EventType
    label: str
    severity: Severity
    signal_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    description: str
    # Piecewise-linear mold temperature deviation (offset_s, delta °C).
    mold_temp_delta: tuple[tuple[float, float], ...] = ((0.0, 0.0),)
    # Step changes of the holding pressure setpoint (offset_s, bar).
    hold_setpoints: tuple[tuple[float, float], ...] = ((0.0, 620.0),)
    # Step changes of the cycle-to-cycle peak pressure spread (offset_s, factor).
    peak_spread: tuple[tuple[float, float], ...] = ((0.0, 1.0),)
    # Single-cycle injection pressure spikes (offset_s).
    pressure_spikes: tuple[float, ...] = ()
    # Intermittent drive faults (offset_s, duration_s): current/vibration up, alarm on.
    fault_windows: tuple[tuple[float, float], ...] = ()
    # Alarm windows independent of drive faults (offset_s, duration_s).
    alarm_windows: tuple[tuple[float, float], ...] = ()
    # Machine stopped, no cycles (offset_s, duration_s).
    downtimes: tuple[tuple[float, float], ...] = ()
    # Vista B only: worn insert in one nest, (nest, length offset mm, until offset_s).
    worn_nest: tuple[int, float, float] | None = None
    events: tuple[ScenarioEvent, ...] = field(default=())


_BATCH_CHANGE = ScenarioEvent(
    2 * H, None, "batch_change", "Cambio de lote de material (MAT-DEMO-B)", "info", ("barrel_temp",)
)

# Thermal drift: mold temperature reaches +5 °C (alarm threshold 60 °C) at
# 4.875 h on the 3 h -> 6 h ramp, and drops below it again at 6.8125 h.
_THERMAL_ALARM = (4.875 * H, (6.8125 - 4.875) * H)

_PRESSURE_SPIKES = (4.6 * H, 5.3 * H, 6.1 * H, 7.2 * H)

_FAULTS = ((1.2 * H, 90.0), (2.75 * H, 120.0), (3.1 * H, 60.0), (5.35 * H, 150.0), (6.9 * H, 90.0))
_INSERT_CHANGE = (4.0 * H, 20 * 60.0)

SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        id="normal",
        name="Operación normal estable",
        description="Proceso dentro de ventana, variación natural ciclo a ciclo. Referencia para comparar.",
        events=(_BATCH_CHANGE,),
    ),
    Scenario(
        id="thermal_drift",
        name="Deriva térmica del molde",
        description=(
            "A partir de la hora 3 baja el caudal de refrigeración y la temperatura de molde sube "
            "~8 °C en 3 h; se ajusta la refrigeración a la hora 6.5."
        ),
        mold_temp_delta=(
            (0.0, 0.0),
            (3 * H, 0.0),
            (6 * H, 8.0),
            (6.5 * H, 8.0),
            (7.25 * H, 0.8),
            (8 * H, 0.5),
        ),
        alarm_windows=(_THERMAL_ALARM,),
        events=(
            _BATCH_CHANGE,
            ScenarioEvent(
                3 * H,
                3 * H,
                "thermal_instability",
                "Inicio de deriva térmica (caudal de refrigeración reducido)",
                "warning",
                ("mold_temp",),
            ),
            ScenarioEvent(
                _THERMAL_ALARM[0],
                _THERMAL_ALARM[1],
                "alarm",
                "Alarma: temperatura de molde > 60 °C",
                "critical",
                ("mold_temp", "alarm"),
            ),
            ScenarioEvent(
                6.5 * H, None, "intervention", "Ajuste del caudal de refrigeración", "info", ("mold_temp",)
            ),
        ),
    ),
    Scenario(
        id="pressure_setpoint_change",
        name="Cambio de setpoint de presión",
        description=(
            "En la hora 4 se reduce la presión de mantenimiento de 620 a 560 bar; después aumenta la "
            "dispersión de la presión pico y aparecen picos aislados."
        ),
        hold_setpoints=((0.0, 620.0), (4 * H, 560.0)),
        peak_spread=((0.0, 1.0), (4 * H, 3.0)),
        pressure_spikes=_PRESSURE_SPIKES,
        events=(
            _BATCH_CHANGE,
            ScenarioEvent(
                4 * H,
                None,
                "setpoint_change",
                "Cambio de setpoint: presión de mantenimiento 620 → 560 bar",
                "warning",
                ("holding_pressure", "injection_pressure"),
            ),
            *(
                ScenarioEvent(
                    t,
                    None,
                    "pressure_instability",
                    "Pico de presión de inyección",
                    "warning",
                    ("injection_pressure",),
                )
                for t in _PRESSURE_SPIKES
            ),
        ),
    ),
    Scenario(
        id="intermittent_fault_cavity_change",
        name="Fallo intermitente y cambio de inserto",
        description=(
            "Fallos intermitentes de accionamiento (sobrecorriente y vibración) y un paro de 20 min "
            "para cambiar el inserto del nido 7."
        ),
        fault_windows=_FAULTS,
        downtimes=(_INSERT_CHANGE,),
        worn_nest=(7, 0.04, _INSERT_CHANGE[0] + _INSERT_CHANGE[1]),
        events=(
            _BATCH_CHANGE,
            *(
                ScenarioEvent(
                    t,
                    d,
                    "alarm",
                    "Fallo intermitente: sobrecorriente / vibración",
                    "warning",
                    ("motor_current", "vibration", "alarm"),
                )
                for t, d in _FAULTS
            ),
            ScenarioEvent(
                _INSERT_CHANGE[0],
                _INSERT_CHANGE[1],
                "downtime",
                "Paro: cambio de inserto en nido 7",
                "critical",
                ("auto_mode", "cycle_active"),
            ),
            ScenarioEvent(
                _INSERT_CHANGE[0] + _INSERT_CHANGE[1],
                None,
                "tool_change",
                "Arranque tras cambio de inserto (nido 7)",
                "info",
                ("active_cavity",),
            ),
        ),
    ),
)

_BY_ID = {s.id: s for s in SCENARIOS}


def get_scenario(scenario_id: str) -> Scenario:
    """Raises KeyError for an unknown scenario id."""
    return _BY_ID[scenario_id]
