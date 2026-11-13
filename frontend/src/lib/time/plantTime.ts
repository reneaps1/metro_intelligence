// IQ-F10 (plan decision D9): plant local time = UTC + offset. Charts of a REAL
// dataset label instants this way; every other dataset keeps UTC (offset 0).

const MINUTE_MS = 60_000;

/** ISO string of an instant shifted to plant local time (the "Z" is not meaningful). */
function shifted(ms: number, offsetMinutes: number): string {
  return new Date(ms + offsetMinutes * MINUTE_MS).toISOString();
}

/** "MM-DD" in plant local time. */
export function plantDay(ms: number, offsetMinutes = 0): string {
  return shifted(ms, offsetMinutes).slice(5, 10);
}

/** "YYYY-MM-DD HH:MM" in plant local time. */
export function plantMinute(ms: number, offsetMinutes = 0): string {
  return shifted(ms, offsetMinutes).replace("T", " ").slice(0, 16);
}

/** "UTC−05:00" style label for an offset in minutes. */
export function offsetLabel(offsetMinutes: number): string {
  if (!offsetMinutes) return "UTC";
  const sign = offsetMinutes < 0 ? "−" : "+";
  const abs = Math.abs(offsetMinutes);
  return `UTC${sign}${String(Math.floor(abs / 60)).padStart(2, "0")}:${String(abs % 60).padStart(2, "0")}`;
}
