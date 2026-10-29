import type { GroupBy, Granularity } from "./types";

// IQ-F5: filter state shared by demo steps 2 and 3 (kept in the demo session
// so it survives navigation and is cleared by "Restaurar escenario demo").
export const DEMO_DATASET_ID = "demo-synthetic-dimensional";
/** IQ-F10: the customer's REAL dataset, offered only when configured locally. */
export const isRealDatasetId = (id: string) => id.startsWith("real-");
/** Data-quality flag bit for "repeated value signature" (suspected frozen data). */
export const SUSPECT_FLAGS = 2;
/** IQ-F17: data-quality flag bit for "nest / mold cavity normalized by a remap rule". */
export const REMAPPED_FLAGS = 8;

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
  /** IQ-F10: mold cavities (second grouping), stations counted towards NOK, suspect-data exclusion. */
  moldCavities: number[];
  stations: string[];
  excludeSuspect: boolean;
  /** IQ-F17: drop pieces whose nest was normalized (compare with and without the rule). */
  excludeRemapped: boolean;
  /** True once the presenter picked a dataset; until then a REAL dataset is preferred. */
  datasetChosen: boolean;
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
  moldCavities: [],
  stations: [],
  excludeSuspect: false,
  excludeRemapped: false,
  datasetChosen: false,
};

/** "+HH:MM" / "-HH:MM" for a UTC offset in minutes ("Z" for UTC). */
export function offsetSuffix(offsetMinutes: number): string {
  if (!offsetMinutes) return "Z";
  const sign = offsetMinutes < 0 ? "-" : "+";
  const abs = Math.abs(offsetMinutes);
  return `${sign}${String(Math.floor(abs / 60)).padStart(2, "0")}:${String(abs % 60).padStart(2, "0")}`;
}

function nextDay(day: string): string {
  const d = new Date(`${day}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}

/** Query parameters shared by /overview and /variable. Days are plant-local when an offset is given. */
export function filterParams(f: QualityFilters, offsetMinutes = 0): URLSearchParams {
  const params = new URLSearchParams({ dataset: f.datasetId });
  const tz = offsetSuffix(offsetMinutes);
  if (f.startDay) params.set("start", `${f.startDay}T00:00:00${tz}`);
  if (f.endDay) params.set("end", `${nextDay(f.endDay)}T00:00:00${tz}`);
  if (f.moldCavities.length) params.set("mold_cavities", f.moldCavities.join(","));
  const excluded = (f.excludeSuspect ? SUSPECT_FLAGS : 0) | (f.excludeRemapped ? REMAPPED_FLAGS : 0);
  if (excluded) params.set("exclude_flags", String(excluded));
  if (f.machines.length) params.set("machines", f.machines.join(","));
  if (f.cavities.length) params.set("cavities", f.cavities.join(","));
  if (f.shifts.length) params.set("shifts", f.shifts.join(","));
  if (f.batches.length) params.set("batches", f.batches.join(","));
  return params;
}

export function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

const localDay = (iso: string, offsetMinutes: number) =>
  new Date(new Date(iso).getTime() + offsetMinutes * 60_000).toISOString().slice(0, 10);

/** Days ("YYYY-MM-DD") between two ISO timestamps, inclusive (plant local time when an offset is given). */
export function daysBetween(startIso: string, endIso: string, offsetMinutes = 0): string[] {
  const days: string[] = [];
  let day = localDay(startIso, offsetMinutes);
  const last = localDay(endIso, offsetMinutes);
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
    (f.variables.length ? 1 : 0) +
    (f.moldCavities.length ? 1 : 0) +
    (f.stations.length ? 1 : 0) +
    (f.excludeSuspect ? 1 : 0) +
    (f.excludeRemapped ? 1 : 0)
  );
}

export function formatPct(rate: number | null | undefined, digits = 2): string {
  if (rate === null || rate === undefined) return "—";
  return `${(rate * 100).toLocaleString("es-MX", { minimumFractionDigits: digits, maximumFractionDigits: digits })} %`;
}
