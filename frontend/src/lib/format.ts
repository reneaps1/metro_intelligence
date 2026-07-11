import type { Specification } from "./mock/types";

export function formatSpec(spec: Specification): string {
  const { nominal, lowerTol, upperTol, unit } = spec;
  if (lowerTol !== null && upperTol !== null && lowerTol === -upperTol) {
    return `${nominal.toFixed(3)} ±${upperTol.toFixed(3)} ${unit}`;
  }
  const upper = upperTol !== null ? `+${upperTol.toFixed(3)}` : null;
  const lower = lowerTol !== null ? `${lowerTol.toFixed(3)}` : null;
  const bounds = [upper, lower].filter((v): v is string => v !== null).join("/");
  return `${nominal.toFixed(3)} ${bounds} ${unit}`.trim();
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function classificationLabel(classification: string): string {
  if (classification === "critical") return "Critical (CC)";
  if (classification === "significant") return "Significant (SC)";
  return "Standard";
}
