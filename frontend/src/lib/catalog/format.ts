import type { Specification } from "./types";

// Mirrors lib/format.ts's formatSpec, adapted for the real API's Decimal
// (string) fields instead of the mock's numbers.
export function formatSpecification(spec: Specification): string {
  const nominal = Number(spec.nominal);
  const lower = spec.lower_tol !== null ? Number(spec.lower_tol) : null;
  const upper = spec.upper_tol !== null ? Number(spec.upper_tol) : null;
  if (lower !== null && upper !== null && lower === -upper) {
    return `${nominal.toFixed(3)} ±${upper.toFixed(3)} ${spec.unit}`;
  }
  const upperText = upper !== null ? `+${upper.toFixed(3)}` : null;
  const lowerText = lower !== null ? `${lower.toFixed(3)}` : null;
  const bounds = [upperText, lowerText].filter((v): v is string => v !== null).join("/");
  return `${nominal.toFixed(3)} ${bounds} ${spec.unit}`.trim();
}
