import {
  DEFAULT_QUALITY_FILTERS,
  DEMO_DATASET_ID,
  type QualityFilters,
} from "../quality-analytics/filters";
import type { QualityDataset } from "../quality-analytics/types";

// IQ-F22: the part chosen in the workbench's "Pieza" control. Inside the demo
// shell the selection is `qualityFilters.datasetId`; it is also remembered in
// this browser so the full-screen line panel (outside the shell) follows it.
// Storage is a per-viewer convenience: every read/write may fail silently.

const STORAGE_KEY = "mi-demo-part";

export function storedPartId(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function storePartId(id: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, id);
  } catch {
    // Private mode or blocked storage: the selection just is not remembered.
  }
}

/** Fresh filters for a newly selected part (filters of another part never carry over). */
export function partFilters(ds: QualityDataset, chosen = true): QualityFilters {
  return {
    ...DEFAULT_QUALITY_FILTERS,
    datasetId: ds.id,
    datasetChosen: chosen,
    detailVariable:
      ds.id === DEMO_DATASET_ID
        ? DEFAULT_QUALITY_FILTERS.detailVariable
        : (ds.variables[0]?.key ?? ""),
  };
}

/** Datasets whose verdicts come from the machine (REAL parts and their fictitious twins). */
export function usesReportedVerdicts(
  ds: QualityDataset | null | undefined,
): boolean {
  return Boolean(
    ds && ds.nok_basis === "reported" && ds.source_type !== "IMPORTED",
  );
}

interface Groupable {
  id: string;
  line?: string | null;
  source_type: QualityDataset["source_type"];
}

export interface PartGroup<T extends Groupable = QualityDataset> {
  line: string;
  items: T[];
}

/** The part the demo opens with: the one remembered in this browser, else the first REAL one. */
export function initialPartId(items: Groupable[]): string | null {
  const stored = storedPartId();
  const remembered = items.find(
    (d) => d.id === stored && d.source_type !== "IMPORTED",
  );
  return (
    (remembered ?? items.find((d) => d.source_type === "REAL"))?.id ?? null
  );
}

/** Selector entries grouped by line; datasets without a line go under their origin. */
export function groupParts<T extends Groupable>(items: T[]): PartGroup<T>[] {
  const groups: PartGroup<T>[] = [];
  for (const ds of items) {
    const line =
      ds.line ??
      (ds.source_type === "REAL"
        ? "Datos reales"
        : ds.source_type === "IMPORTED"
          ? "Importados (CSV)"
          : "Demo inyección");
    let group = groups.find((g) => g.line === line);
    if (!group) {
      group = { line, items: [] };
      groups.push(group);
    }
    group.items.push(ds);
  }
  return groups;
}

/** IQ-F22: words for the two grouping slots of a dataset (defaults = the injection demo's). */
export function groupWords(
  ds: Pick<QualityDataset, "group_labels"> | null | undefined,
): {
  primary: string;
  secondary: string;
} {
  return {
    primary: ds?.group_labels?.primary ?? "Nido",
    secondary: ds?.group_labels?.secondary ?? "Cavidad de molde",
  };
}

/** IQ-F25: short axis prefix for a grouping slot ("C" for Cavidad, "N" for Nido, "L" for Lado), if labelled. */
export function groupPrefix(
  ds: Pick<QualityDataset, "group_labels"> | null | undefined,
  slot: "primary" | "secondary",
): string | undefined {
  const label = ds?.group_labels?.[slot];
  return label ? label.charAt(0).toUpperCase() : undefined;
}

/** IQ-F25: display value of the secondary slot: "Izq"/"Der" for sides, "C<n>" for mold cavities. */
export function sideOrCavity(
  ds: Pick<QualityDataset, "group_labels"> | null | undefined,
  value: number,
): string {
  if (ds?.group_labels?.secondary === "Lado")
    return value === 1 ? "Izq" : value === 2 ? "Der" : `L${value}`;
  return `C${value}`;
}
