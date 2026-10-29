import { DEFAULT_SCENARIO_ID } from "./DemoSessionProvider";

// Demo workbench (design-system.md §4.1): alarms the industrial demo derives
// from the simulated scenario. They are not produced by any engine or machine
// -- the UI labels them "Simulada" -- and only illustrate ISA-101 alarm
// handling (priority by shape, acknowledge, summary one click away).

export type AlarmPriority = 1 | 2;

export interface SimulatedAlarm {
  id: string;
  priority: AlarmPriority;
  /** Fictitious signal tag of the demo machine. */
  tag: string;
  text: string;
  /** Offset from the scenario start, as the simulator timeline shows it. */
  at: string;
}

const SCENARIO_ALARMS: Record<string, SimulatedAlarm[]> = {
  thermal_drift: [
    { id: "thermal_drift:tmolde", priority: 2, tag: "INY01.TMOLDE", text: "Temperatura de molde en deriva ascendente", at: "T+02:40" },
  ],
  pressure_setpoint_change: [
    { id: "pressure:sp", priority: 2, tag: "INY01.PMANT.SP", text: "Cambio de setpoint de presión de mantenimiento", at: "T+01:50" },
  ],
  intermittent_fault_cavity_change: [
    { id: "fault:estado", priority: 1, tag: "INY01.ESTADO", text: "Fallo intermitente de máquina", at: "T+00:20" },
    { id: "fault:inserto", priority: 2, tag: "INY01.MOLDE.INSERTO", text: "Cambio de inserto en un nido", at: "T+02:05" },
  ],
};

export function alarmsForScenario(scenarioId: string): SimulatedAlarm[] {
  return SCENARIO_ALARMS[scenarioId] ?? [];
}

export function isAbnormalScenario(scenarioId: string): boolean {
  return scenarioId !== DEFAULT_SCENARIO_ID;
}

/** Highest priority (lowest number) among the alarms, or null when there are none. */
export function topPriority(alarms: SimulatedAlarm[]): AlarmPriority | null {
  if (alarms.length === 0) return null;
  return alarms.some((a) => a.priority === 1) ? 1 : 2;
}
