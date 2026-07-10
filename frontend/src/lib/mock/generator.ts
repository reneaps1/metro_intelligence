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
