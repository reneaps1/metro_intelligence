import type { GroupBy, Granularity } from "./types";

// IQ-F5: filter state shared by demo steps 2 and 3 (kept in the demo session
// so it survives navigation and is cleared by "Restaurar escenario demo").
export const DEMO_DATASET_ID = "demo-synthetic-dimensional";

export interface QualityFilters {
  datasetId: string;
  /** Inclusive day range, "YYYY-MM-DD"; null = open */
  startDay: string | null;
  endDay: string | null;
  machines: string[];
  cavities: number[];
  shifts: string[];
  batches: string[];
  /** Variables counted towards piece NOK; empty = all */
  variables: string[];
  granularity: Granularity;
  /** Variable shown in the dimensional exploration step */
  detailVariable: string;
  groupBy: GroupBy;
}

export const DEFAULT_QUALITY_FILTERS: QualityFilters = {
  datasetId: DEMO_DATASET_ID,
  startDay: null,
  endDay: null,
  machines: [],
  cavities: [],
  shifts: [],
  batches: [],
  variables: [],
  granularity: "day",
  detailVariable: "PinsLength",
  groupBy: "cavity",
};

function nextDay(day: string): string {
  const d = new Date(`${day}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}

/** Query parameters shared by /overview and /variable. */
export function filterParams(f: QualityFilters): URLSearchParams {
  const params = new URLSearchParams({ dataset: f.datasetId });
  if (f.startDay) params.set("start", `${f.startDay}T00:00:00Z`);
  if (f.endDay) params.set("end", `${nextDay(f.endDay)}T00:00:00Z`);
  if (f.machines.length) params.set("machines", f.machines.join(","));
  if (f.cavities.length) params.set("cavities", f.cavities.join(","));
  if (f.shifts.length) params.set("shifts", f.shifts.join(","));
  if (f.batches.length) params.set("batches", f.batches.join(","));
  return params;
}

export function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

/** Days ("YYYY-MM-DD") between two ISO timestamps, inclusive. */
export function daysBetween(startIso: string, endIso: string): string[] {
  const days: string[] = [];
  let day = startIso.slice(0, 10);
  const last = endIso.slice(0, 10);
  while (day <= last && days.length < 400) {
    days.push(day);
    day = nextDay(day);
  }
  return days;
}

export function activeFilterCount(f: QualityFilters): number {
  return (
    (f.startDay || f.endDay ? 1 : 0) +
    (f.machines.length ? 1 : 0) +
    (f.cavities.length ? 1 : 0) +
    (f.shifts.length ? 1 : 0) +
    (f.batches.length ? 1 : 0) +
    (f.variables.length ? 1 : 0)
  );
}

export function formatPct(rate: number | null | undefined, digits = 2): string {
  if (rate === null || rate === undefined) return "—";
  return `${(rate * 100).toLocaleString("es-MX", { minimumFractionDigits: digits, maximumFractionDigits: digits })} %`;
}
