// IQ-F16: chart styling of the industrial workbench (design-system.md §4.3),
// taken from the line panel. Marks are neutral; what is NOK or out of pattern
// (worst group, NOK points, outliers) takes the muted NOK accent, a neutral
// emphasis takes the dark mark, and references and limits are drawn in the
// text color and labelled at their end. Alarm colors stay for marks that ask
// for action, and signal pens (IIoT tracks) keep the categorical --chart-*
// palette because each pen is a different signal.

export const WB = {
  bar: "var(--wb-bar)",
  mark: "var(--wb-mark)",
  soft: "var(--wb-mark-soft)",
  nok: "var(--wb-nok)",
  ref: "var(--text-primary)",
  text: "var(--text-secondary)",
  grid: "var(--border-default)",
} as const;

export const axisTick = { fontSize: 11, fill: "var(--text-secondary)" };

export const tooltipStyle = {
  background: "var(--bg-surface-raised)",
  border: "1px solid var(--border-default)",
  borderRadius: 6,
  fontSize: 12,
};

/** Faint horizontal grid for line charts; bar charts go without one. */
export const gridProps = { stroke: "var(--border-default)", strokeOpacity: 0.35, vertical: false } as const;

/** A comparison or cumulative series: thin dashed line in the text color. */
export const secondaryLine = { stroke: "var(--text-primary)", strokeWidth: 1.5, strokeDasharray: "5 4" } as const;

/** Reference line (dotted) and limit line (dashed), as on the panel. */
export const refLine = { stroke: "var(--text-primary)", strokeWidth: 1.5, strokeDasharray: "2 4" } as const;
export const limitLine = { stroke: "var(--text-primary)", strokeWidth: 2, strokeDasharray: "7 5" } as const;

/**
 * Uppercase label at the end of a reference or limit line ("REF. 3.2 %").
 * "right" sets it in the plot's right margin (leave ~72 px), clear of the marks.
 */
export function lineLabel(
  value: string,
  position: "right" | "insideTopRight" | "insideBottomRight" | "insideTopLeft" = "right",
) {
  return { value: value.toUpperCase(), position, fill: "var(--text-primary)", fontSize: 10, fontWeight: 700 };
}

/** Value label on top of bars (monospaced, like the panel). */
export const barValueLabel = {
  position: "top" as const,
  fill: "var(--text-primary)",
  fontSize: 10,
  fontFamily: "JetBrains Mono, ui-monospace, monospace",
  fontWeight: 600,
};

/** Single-hue neutral ramp: share in [0, 1] -> background and readable text. */
export function rampFill(share: number): { background: string; color: string } {
  const a = Math.max(0, Math.min(1, share));
  return {
    background: `rgba(var(--wb-ramp), ${(0.08 + a * 0.85).toFixed(2)})`,
    color: a > 0.5 ? "var(--bg-surface)" : "var(--text-primary)",
  };
}
