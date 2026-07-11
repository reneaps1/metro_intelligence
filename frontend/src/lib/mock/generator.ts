// Deterministic pseudo-random generation so the demo is reproducible
// (docs/seed-data-strategy.md: "deterministic with fixed random seed").
function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function makeRng(seed: number) {
  const rand = mulberry32(seed);
  return {
    next: () => rand(),
    gaussian: (mean: number, stdDev: number) => {
      const u1 = Math.max(rand(), 1e-9);
      const u2 = rand();
      const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
      return mean + z * stdDev;
    },
  };
}

export function mean(values: number[]): number {
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

export function stdDev(values: number[]): number {
  const m = mean(values);
  const variance = values.reduce((sum, v) => sum + (v - m) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

/** Simplified Cpk: min((USL-mean), (mean-LSL)) / (3*stdDev), unilateral-aware. */
export function cpk(values: number[], nominal: number, lowerTol: number | null, upperTol: number | null): number {
  const m = mean(values);
  const sd = stdDev(values) || 1e-6;
  const upper = upperTol === null ? Infinity : (nominal + upperTol - m) / (3 * sd);
  const lower = lowerTol === null ? Infinity : (m - (nominal + lowerTol)) / (3 * sd);
  return Math.min(upper, lower);
}

/** Simulates newly-imported samples continuing a characteristic's recent local
 * behavior (not the full lifetime pattern) — good enough for "an import just
 * landed a few new points" without re-deriving the original generator seed. */
export function simulateNewPoints(
  spec: { nominal: number; lowerTol: number | null; upperTol: number | null },
  existingPoints: { value: number; sampleIndex: number }[],
  count: number,
  fromDate: Date,
  seed: number
) {
  const recent = existingPoints.slice(-8).map((p) => p.value);
  const localMean = recent.length ? mean(recent) : spec.nominal;
  const tolSpan = Math.abs(spec.upperTol ?? spec.lowerTol ?? 0.1) + Math.abs(spec.lowerTol ?? spec.upperTol ?? 0.1);
  const localStd = recent.length > 1 ? stdDev(recent) || tolSpan / 12 : tolSpan / 12;
  const rng = makeRng(seed);
  const lastIndex = existingPoints.at(-1)?.sampleIndex ?? 0;

  return Array.from({ length: count }, (_, i) => {
    const value = rng.gaussian(localMean, localStd);
    const deviation = value - spec.nominal;
    const isOk =
      (spec.lowerTol === null || deviation >= spec.lowerTol) && (spec.upperTol === null || deviation <= spec.upperTol);
    return {
      measuredAt: new Date(fromDate.getTime() + i * 60_000).toISOString(),
      value: Math.round(value * 1e6) / 1e6,
      deviation: Math.round(deviation * 1e6) / 1e6,
      isOk,
      sampleIndex: lastIndex + i + 1,
    };
  });
}
