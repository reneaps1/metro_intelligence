// IQ-F4: plain-language reading of a correlation, worded as association /
// hypothesis -- never as cause (CLAUDE.md §22, prompt §7.E).
export function describeCorrelation(r: number | null): string {
  if (r === null) return "Correlación no definida (muy pocos pares o una señal constante).";
  const abs = Math.abs(r);
  const direction = r > 0 ? "positiva" : "negativa";
  if (abs < 0.1) return "Sin asociación lineal apreciable.";
  if (abs < 0.3) return `Asociación lineal ${direction} débil.`;
  if (abs < 0.6) return `Asociación lineal ${direction} moderada.`;
  return `Asociación lineal ${direction} fuerte.`;
}

/** Compact number for equations: 4 significant digits, no exponent for normal ranges. */
export function formatCoefficient(value: number | null): string {
  if (value === null) return "—";
  if (value === 0) return "0";
  const abs = Math.abs(value);
  if (abs >= 1e-4 && abs < 1e6) return Number(value.toPrecision(4)).toString();
  return value.toExponential(3);
}

export function equation(slope: number | null, intercept: number | null): string {
  if (slope === null || intercept === null) return "—";
  const sign = slope < 0 ? "−" : "+";
  return `y = ${formatCoefficient(intercept)} ${sign} ${formatCoefficient(Math.abs(slope))} · x`;
}
