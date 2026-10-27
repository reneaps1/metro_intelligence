import { describe, expect, it } from "vitest";
import { DEFAULT_QUALITY_FILTERS, activeFilterCount, daysBetween, filterParams, formatPct, toggle } from "./filters";
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

  it("exports the per-nest table as aggregated CSV", () => {
    const csv = cavityCsv([{ cavity: 4, pieces: 300, nok: 28, rate: 28 / 300, ci_low: 0.06, ci_high: 0.13, relative_risk: null }]);
    expect(csv.split("\n")).toEqual([
      "nido,piezas,nok,tasa_nok,ic95_inf,ic95_sup,riesgo_relativo",
      "4,300,28,0.093333,0.06,0.13,",
    ]);
  });
});
