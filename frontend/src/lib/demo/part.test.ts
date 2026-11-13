import { describe, expect, it } from "vitest";
import type { QualityDataset } from "../quality-analytics/types";
import { groupParts, groupWords, usesReportedVerdicts } from "./part";

const ds = (over: Partial<QualityDataset>) => ({ id: "x", name: "x", source_type: "SIMULATED", ...over }) as QualityDataset;

describe("part selection helpers (IQ-F22)", () => {
  it("groups parts by line, falling back to their origin", () => {
    const groups = groupParts([
      ds({ id: "demo-synthetic-dimensional" }),
      ds({ id: "demo-b1", line: "Línea demo B" }),
      ds({ id: "demo-a1", line: "Línea demo A" }),
      ds({ id: "demo-b2", line: "Línea demo B" }),
      ds({ id: "import-1", source_type: "IMPORTED" }),
    ]);
    expect(groups.map((g) => [g.line, g.items.map((i) => i.id)])).toEqual([
      ["Demo inyección", ["demo-synthetic-dimensional"]],
      ["Línea demo B", ["demo-b1", "demo-b2"]],
      ["Línea demo A", ["demo-a1"]],
      ["Importados (CSV)", ["import-1"]],
    ]);
  });

  it("uses the dataset's grouping vocabulary with the injection demo as default", () => {
    expect(groupWords(ds({}))).toEqual({ primary: "Nido", secondary: "Cavidad de molde" });
    expect(groupWords(ds({ group_labels: { primary: "Cavidad" } }))).toEqual({
      primary: "Cavidad",
      secondary: "Cavidad de molde",
    });
    expect(groupWords(ds({ group_labels: { primary: "Nido", secondary: "Lado" } })).secondary).toBe("Lado");
  });

  it("runs per-piece studies only on machine-reported verdicts that are not CSV imports", () => {
    expect(usesReportedVerdicts(ds({ nok_basis: "reported" }))).toBe(true);
    expect(usesReportedVerdicts(ds({ nok_basis: "spec" }))).toBe(false);
    expect(usesReportedVerdicts(ds({ nok_basis: "reported", source_type: "IMPORTED" }))).toBe(false);
    expect(usesReportedVerdicts(null)).toBe(false);
  });
});
