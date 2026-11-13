import type { ChipStatus } from "../../components/ui/StatusChip";
import type { Operation, SpecLimits, StepStatus } from "./types";

export const STATUS_LABEL: Record<StepStatus, string> = {
  ok: "In control",
  warning: "Watch",
  critical: "Action needed",
  neutral: "No data",
};

export function stepChipStatus(status: StepStatus): ChipStatus {
  return status;
}

const KIND_LABEL: Record<Operation["kind"], string> = {
  electrical: "Electrical test",
  pin_length: "Pin length",
  pin_position: "Pin position",
  type_check: "Type check",
};

export function operationKindLabel(operation: Operation): string {
  const side = operation.side === "pcb" ? " · PCB side" : operation.side === "connector" ? " · Connector side" : "";
  return `${KIND_LABEL[operation.kind]}${side}`;
}

export function formatCount(value: number): string {
  return value.toLocaleString("en-US");
}

export function formatPercent(rate: number | null, digits = 2): string {
  return rate === null ? "—" : `${(rate * 100).toFixed(digits)}%`;
}

export function formatNumber(value: number | null, digits = 3): string {
  return value === null ? "—" : value.toFixed(digits);
}

export function formatLimits(spec: SpecLimits | null, unit: string): string {
  if (spec === null) return "No specification";
  const lower = spec.lower_limit !== null ? Number(spec.lower_limit).toFixed(3) : null;
  const upper = spec.upper_limit !== null ? Number(spec.upper_limit).toFixed(3) : null;
  if (lower !== null && upper !== null) return `${lower} – ${upper} ${unit}`;
  if (upper !== null) return `≤ ${upper} ${unit}`;
  return `≥ ${lower} ${unit}`;
}

export function formatDay(isoDay: string): string {
  return new Date(`${isoDay}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function formatRange(start: string, end: string): string {
  const opts: Intl.DateTimeFormatOptions = { year: "numeric", month: "short", day: "numeric" };
  const a = new Date(`${start}T00:00:00`).toLocaleDateString("en-US", opts);
  const b = new Date(`${end}T00:00:00`).toLocaleDateString("en-US", opts);
  return start === end ? a : `${a} – ${b}`;
}
