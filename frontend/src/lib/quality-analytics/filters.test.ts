import { describe, expect, it } from "vitest";
import {
  DEFAULT_QUALITY_FILTERS,
  DEMO_DATASET_ID,
  activeFilterCount,
  daysBetween,
  filterParams,
  formatPct,
  offsetSuffix,
  toggle,
} from "./filters";
import { stepOrigins } from "../demo/stepOrigins";
import { DEMO_STEPS } from "../demo/steps";
import { cavityCsv } from "./export";

describe("quality filters", () => {
  it("serialises filters, closing the day range at the next midnight", () => {
    const params = filterParams({
      ...DEFAULT_QUALITY_FILTERS,
      startDay: "2026-10-14",
      endDay: "2026-10-15",
      machines: ["INY-01"],
      cavities: [4, 9],
      shifts: ["C"],
    });
    expect(params.get("start")).toBe("2026-10-14T00:00:00Z");
    expect(params.get("end")).toBe("2026-10-16T00:00:00Z");
    expect(params.get("cavities")).toBe("4,9");
    expect(params.get("machines")).toBe("INY-01");
    expect(params.get("batches")).toBeNull();
  });

  it("handles month boundaries and helpers", () => {
    expect(filterParams({ ...DEFAULT_QUALITY_FILTERS, endDay: "2026-10-31" }).get("end")).toBe("2026-11-01T00:00:00Z");
    expect(toggle([1, 2], 2)).toEqual([1]);
    expect(toggle([1], 3)).toEqual([1, 3]);
    expect(daysBetween("2026-10-13T00:00:00Z", "2026-10-15T23:00:00Z")).toEqual(["2026-10-13", "2026-10-14", "2026-10-15"]);
    expect(activeFilterCount(DEFAULT_QUALITY_FILTERS)).toBe(0);
    expect(activeFilterCount({ ...DEFAULT_QUALITY_FILTERS, cavities: [4], startDay: "2026-10-14" })).toBe(2);
    expect(formatPct(0.0938)).toBe("9.38 %");
    expect(formatPct(null)).toBe("—");
  });

  it("uses plant local days and serialises the REAL dataset filters", () => {
    const params = filterParams(
      { ...DEFAULT_QUALITY_FILTERS, startDay: "2026-01-05", endDay: "2026-01-05", moldCavities: [3, 17], excludeSuspect: true },
      -300,
    );
    expect(params.get("start")).toBe("2026-01-05T00:00:00-05:00");
    expect(params.get("end")).toBe("2026-01-06T00:00:00-05:00");
    expect(params.get("mold_cavities")).toBe("3,17");
    expect(params.get("exclude_flags")).toBe("2");
    expect(offsetSuffix(330)).toBe("+05:30");
    // 2026-01-06T03:00Z is still the 5th in plant time (UTC-5).
    expect(daysBetween("2026-01-05T13:00:00Z", "2026-01-06T03:00:00Z", -300)).toEqual(["2026-01-05"]);
    expect(activeFilterCount({ ...DEFAULT_QUALITY_FILTERS, stations: ["a"], moldCavities: [1], excludeSuspect: true })).toBe(3);
  });

  it("combines the suspect and remapped-nest exclusions into one flag mask (IQ-F17)", () => {
    const both = filterParams({ ...DEFAULT_QUALITY_FILTERS, excludeSuspect: true, excludeRemapped: true });
    expect(both.get("exclude_flags")).toBe("10");
    expect(filterParams({ ...DEFAULT_QUALITY_FILTERS, excludeRemapped: true }).get("exclude_flags")).toBe("8");
    expect(filterParams(DEFAULT_QUALITY_FILTERS).has("exclude_flags")).toBe(false);
    expect(activeFilterCount({ ...DEFAULT_QUALITY_FILTERS, excludeRemapped: true })).toBe(1);
  });

  it("labels the REAL dataset as real in steps 2 and 3", () => {
    const quality = DEMO_STEPS.find((s) => s.id === "quality")!;
    const dimensional = DEMO_STEPS.find((s) => s.id === "dimensional")!;
    expect(stepOrigins(quality, "real-dimensional")).toEqual(["REAL", "PRECOMPUTED"]);
    expect(stepOrigins(dimensional, "real-dimensional")).toEqual(["REAL"]);
    expect(stepOrigins(quality, "import-1")).toEqual(["HISTORICAL"]);
    expect(stepOrigins(quality, DEMO_DATASET_ID)).toEqual(quality.origins);
    const ai = DEMO_STEPS.find((s) => s.id === "ai")!;
    expect(stepOrigins(ai, DEMO_DATASET_ID, "real-dimensional")).toEqual(["REAL", ...ai.origins]);
    expect(stepOrigins(ai, DEMO_DATASET_ID, null)).toEqual(ai.origins);
    const correlation = DEMO_STEPS.find((s) => s.id === "correlation")!;
    expect(stepOrigins(correlation, "real-dimensional")).toEqual(["REAL", ...correlation.origins]);
    expect(stepOrigins(correlation, DEMO_DATASET_ID)).toEqual(correlation.origins);
  });

  it("exports the per-nest table as aggregated CSV", () => {
    const csv = cavityCsv([{ cavity: 4, pieces: 300, nok: 28, rate: 28 / 300, ci_low: 0.06, ci_high: 0.13, relative_risk: null }]);
    expect(csv.split("\n")).toEqual([
      "nido,piezas,nok,tasa_nok,ic95_inf,ic95_sup,riesgo_relativo",
      "4,300,28,0.093333,0.06,0.13,",
    ]);
  });
});
