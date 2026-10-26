"""Signal catalog and plant hierarchy for the process simulator.

Hierarchy: plant -> area -> line -> machine -> signal group -> channel. All
names and codes are fictitious. Magnitudes are generic for a mid-size
injection-moulding machine and are NOT specifications of any real equipment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ValueType = Literal["analog", "digital", "discrete", "counter"]
# How a channel's value evolves in time:
# - profile:    intra-cycle waveform (injection, holding, recovery...), sampled fast
# - continuous: slow physical variable sampled at a fixed rate
# - per_cycle:  one value per machine cycle, held until the next cycle (step)
# - state:      machine/scenario state (auto mode, alarm), sampled at a fixed rate
Sampling = Literal["profile", "continuous", "per_cycle", "state"]

SOURCE_TYPE = "SIMULATED"


@dataclass(frozen=True)
class SignalDefinition:
    key: str
    name: str
    group: str
    unit: str
    value_type: ValueType
    sampling: Sampling
    # Native sampling rate; None for per-cycle channels (one value per cycle).
    rate_hz: float | None
    # False for negative-control channels that carry no process information.
    informative: bool
    description: str
    # IQ-F4 "Vista B": synthetic quality channel whose dependence on process
    # signals was imposed on purpose to demonstrate the analysis technique.
    causal_imposed: bool = False


@dataclass(frozen=True)
class MachineDefinition:
    code: str
    name: str
    # Scenario deviations (drift, setpoint change, faults) are injected on the
    # primary machine only; the other one stays nominal as a comparison.
    primary: bool


PLANT = ("PLANTA-DEMO", "Planta demo (ficticia)")
AREA = ("INYECCION", "Área de inyección")
LINE = ("L1", "Línea 1")

MACHINES: tuple[MachineDefinition, ...] = (
    MachineDefinition("INY-01", "Inyectora 01", primary=True),
    MachineDefinition("INY-02", "Inyectora 02", primary=False),
)

GROUPS: dict[str, str] = {
    "temperatures": "Temperaturas",
    "pressures": "Presiones",
    "screw": "Tornillo / inyección",
    "times": "Tiempos",
    "drive": "Accionamiento",
    "state": "Estado de máquina",
    "counters": "Ciclo y contadores",
    "ambient": "Ambiente (señales de control)",
    "quality_sim": "Calidad sintética (Vista B · causalidad impuesta)",
}

SIGNALS: tuple[SignalDefinition, ...] = (
    SignalDefinition(
        "barrel_temp",
        "Temperatura de cilindro",
        "temperatures",
        "°C",
        "analog",
        "continuous",
        1.0,
        True,
        "Temperatura de la zona de alimentación del cilindro.",
    ),
    SignalDefinition(
        "mold_temp",
        "Temperatura de molde",
        "temperatures",
        "°C",
        "analog",
        "continuous",
        1.0,
        True,
        "Temperatura superficial del molde (lado fijo).",
    ),
    SignalDefinition(
        "injection_pressure",
        "Presión de inyección",
        "pressures",
        "bar",
        "analog",
        "profile",
        10.0,
        True,
        "Presión hidráulica específica durante llenado, mantenimiento y dosificación.",
    ),
    SignalDefinition(
        "holding_pressure",
        "Presión de mantenimiento (media por ciclo)",
        "pressures",
        "bar",
        "analog",
        "per_cycle",
        None,
        True,
        "Presión media real durante la fase de compactación.",
    ),
    SignalDefinition(
        "injection_speed",
        "Velocidad de inyección",
        "screw",
        "mm/s",
        "analog",
        "profile",
        10.0,
        True,
        "Velocidad de avance del tornillo durante el llenado.",
    ),
    SignalDefinition(
        "screw_position",
        "Posición del tornillo",
        "screw",
        "mm",
        "analog",
        "profile",
        10.0,
        True,
        "Posición axial del tornillo (0 = adelante).",
    ),
    SignalDefinition(
        "cooling_time",
        "Tiempo de enfriamiento",
        "times",
        "s",
        "analog",
        "per_cycle",
        None,
        True,
        "Tiempo de enfriamiento configurado en el ciclo.",
    ),
    SignalDefinition(
        "cycle_time",
        "Tiempo de ciclo",
        "times",
        "s",
        "analog",
        "per_cycle",
        None,
        True,
        "Duración real del ciclo completo.",
    ),
    SignalDefinition(
        "motor_current",
        "Corriente de motor",
        "drive",
        "A",
        "analog",
        "profile",
        10.0,
        True,
        "Corriente del motor principal de la bomba/accionamiento.",
    ),
    SignalDefinition(
        "vibration",
        "Vibración (RMS)",
        "drive",
        "mm/s",
        "analog",
        "continuous",
        1.0,
        True,
        "Velocidad de vibración RMS en el grupo motor-bomba.",
    ),
    SignalDefinition(
        "active_cavity",
        "Nido activo",
        "counters",
        "nido",
        "discrete",
        "per_cycle",
        None,
        True,
        "Nido/cavidad que recibe el disparo actual (mesa rotativa).",
    ),
    SignalDefinition(
        "shot_counter",
        "Contador de disparos",
        "counters",
        "ciclo",
        "counter",
        "per_cycle",
        None,
        True,
        "Contador acumulado de disparos (ID de ciclo).",
    ),
    SignalDefinition(
        "cycle_active",
        "Ciclo activo (molde cerrado)",
        "state",
        "0/1",
        "digital",
        "profile",
        10.0,
        True,
        "1 mientras el molde está cerrado y el ciclo en curso.",
    ),
    SignalDefinition(
        "auto_mode",
        "Máquina en automático",
        "state",
        "0/1",
        "digital",
        "state",
        1.0,
        True,
        "1 en modo automático; 0 durante paros o intervención manual.",
    ),
    SignalDefinition(
        "alarm",
        "Alarma activa",
        "state",
        "0/1",
        "digital",
        "state",
        1.0,
        True,
        "1 mientras hay una alarma de máquina activa.",
    ),
    SignalDefinition(
        "process_ok",
        "OK de proceso",
        "state",
        "0/1",
        "digital",
        "per_cycle",
        None,
        True,
        "1 si el ciclo quedó dentro de la ventana de proceso (presiones, temperatura, sin fallo).",
    ),
    SignalDefinition(
        "ambient_humidity",
        "Humedad ambiente",
        "ambient",
        "%HR",
        "analog",
        "continuous",
        1.0,
        False,
        "Señal de control: no tiene relación con el proceso en la simulación.",
    ),
    SignalDefinition(
        "aux_voltage",
        "Tensión auxiliar 24 V",
        "ambient",
        "V",
        "analog",
        "continuous",
        1.0,
        False,
        "Señal de control: alimentación auxiliar estable, no informativa.",
    ),
    SignalDefinition(
        "dim_pins_length",
        "Longitud de pin (sintética)",
        "quality_sim",
        "mm",
        "analog",
        "per_cycle",
        None,
        True,
        "Cota sintética inspeccionada 5 min después de cada ciclo. Mecanismo impuesto: depende de la "
        "temperatura de molde, la presión de mantenimiento y el nido. Tolerancia 12.000 ± 0.050 mm.",
        causal_imposed=True,
    ),
    SignalDefinition(
        "dim_nok",
        "NOK dimensional (sintético)",
        "quality_sim",
        "0/1",
        "digital",
        "per_cycle",
        None,
        True,
        "1 si la longitud sintética queda fuera de tolerancia. Disponible 5 min después del ciclo.",
        causal_imposed=True,
    ),
)

_SIGNALS_BY_KEY = {s.key: s for s in SIGNALS}
_MACHINES_BY_CODE = {m.code: m for m in MACHINES}


def signal_id(machine_code: str, key: str) -> str:
    return f"{LINE[0]}.{machine_code}.{key}"


def parse_signal_id(value: str) -> tuple[MachineDefinition, SignalDefinition]:
    """Resolve a signal id like ``L1.INY-01.mold_temp``; raises KeyError if unknown."""
    parts = value.split(".")
    if len(parts) != 3 or parts[0] != LINE[0]:
        raise KeyError(value)
    machine = _MACHINES_BY_CODE.get(parts[1])
    signal = _SIGNALS_BY_KEY.get(parts[2])
    if machine is None or signal is None:
        raise KeyError(value)
    return machine, signal


def get_signal(key: str) -> SignalDefinition:
    return _SIGNALS_BY_KEY[key]


def _signal_leaf(machine: MachineDefinition, signal: SignalDefinition) -> dict[str, Any]:
    sid = signal_id(machine.code, signal.key)
    return {
        "id": sid,
        "name": signal.name,
        "node_type": "signal",
        "children": [],
        "signal": {
            "signal_id": sid,
            "key": signal.key,
            "machine_code": machine.code,
            "name": signal.name,
            "unit": signal.unit,
            "value_type": signal.value_type,
            "sampling": signal.sampling,
            "rate_hz": signal.rate_hz,
            "informative": signal.informative,
            "description": signal.description,
            "source_type": SOURCE_TYPE,
            "causal_imposed": signal.causal_imposed,
        },
    }


def build_tree() -> dict[str, Any]:
    """Plant hierarchy as nested nodes, ready for the API schema."""
    machines = []
    for machine in MACHINES:
        groups = []
        for group_key, group_name in GROUPS.items():
            leaves = [_signal_leaf(machine, s) for s in SIGNALS if s.group == group_key]
            groups.append(
                {
                    "id": f"{LINE[0]}.{machine.code}.{group_key}",
                    "name": group_name,
                    "node_type": "group",
                    "children": leaves,
                    "signal": None,
                }
            )
        machines.append(
            {
                "id": f"{LINE[0]}.{machine.code}",
                "name": machine.name,
                "node_type": "machine",
                "children": groups,
                "signal": None,
            }
        )
    line = {"id": LINE[0], "name": LINE[1], "node_type": "line", "children": machines, "signal": None}
    area = {"id": AREA[0], "name": AREA[1], "node_type": "area", "children": [line], "signal": None}
    return {"id": PLANT[0], "name": PLANT[1], "node_type": "plant", "children": [area], "signal": None}
