import { cpk } from "./generator";
import type { Characteristic, MeasurementPoint } from "./types";

export function cpkForCharacteristic(characteristic: Characteristic, points: MeasurementPoint[]): number {
  const { nominal, lowerTol, upperTol } = characteristic.specification;
  return cpk(
    points.map((p) => p.value),
    nominal,
    lowerTol,
    upperTol
  );
}

/** Buckets a series into `weeks` equal chunks and scores each 0-100 by how
 * close the worst deviation in that chunk came to the tolerance limit —
 * a stand-in for a real time-varying risk assessment (F9), reusing the same
 * generated series the trend chart shows rather than inventing parallel data. */
export function weeklyRiskProxy(
  characteristic: Characteristic,
  points: MeasurementPoint[],
  weeks = 6
): number[] {
  const { lowerTol, upperTol } = characteristic.specification;
  const halfSpan = Math.max(
    upperTol !== null ? Math.abs(upperTol) : Math.abs(lowerTol ?? 1),
    lowerTol !== null ? Math.abs(lowerTol) : Math.abs(upperTol ?? 1)
  );
  const chunkSize = Math.ceil(points.length / weeks);
  const scores: number[] = [];
  for (let w = 0; w < weeks; w++) {
    const chunk = points.slice(w * chunkSize, (w + 1) * chunkSize);
    if (chunk.length === 0) {
      scores.push(0);
      continue;
    }
    const worst = Math.max(...chunk.map((p) => Math.abs(p.deviation)));
    scores.push(Math.min(100, Math.round((worst / halfSpan) * 100)));
  }
  return scores;
}

/** Weekly OK-rate (%) across a combined set of series, oldest to newest. */
export function weeklyAggregateOkRate(seriesList: MeasurementPoint[][], weeks = 6): number[] {
  const all = seriesList.flat().sort((a, b) => a.measuredAt.localeCompare(b.measuredAt));
  if (all.length === 0) return Array(weeks).fill(100);
  const chunkSize = Math.ceil(all.length / weeks);
  const rates: number[] = [];
  for (let w = 0; w < weeks; w++) {
    const chunk = all.slice(w * chunkSize, (w + 1) * chunkSize);
    if (chunk.length === 0) {
      rates.push(rates.at(-1) ?? 100);
      continue;
    }
    const okCount = chunk.filter((p) => p.isOk).length;
    rates.push(Math.round((okCount / chunk.length) * 100));
  }
  return rates;
}

export function histogramBins(points: MeasurementPoint[], binCount = 10): { x0: number; x1: number; count: number }[] {
  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const width = (max - min || 1) / binCount;
  const bins = Array.from({ length: binCount }, (_, i) => ({ x0: min + i * width, x1: min + (i + 1) * width, count: 0 }));
  for (const v of values) {
    const idx = Math.min(binCount - 1, Math.floor((v - min) / width));
    bins[idx].count += 1;
  }
  return bins;
}
