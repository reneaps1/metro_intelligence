import type { CavityRate } from "./types";

// IQ-F5: aggregated (never raw) CSV export of the per-nest table.
export function cavityCsv(rows: CavityRate[]): string {
  const header = "nido,piezas,nok,tasa_nok,ic95_inf,ic95_sup,riesgo_relativo";
  const fmt = (v: number | null) => (v === null ? "" : String(Number(v.toFixed(6))));
  const lines = rows.map((r) =>
    [r.cavity, r.pieces, r.nok, fmt(r.rate), fmt(r.ci_low), fmt(r.ci_high), fmt(r.relative_risk)].join(","),
  );
  return [header, ...lines].join("\n");
}

export function downloadText(filename: string, text: string, mime = "text/csv"): void {
  const url = URL.createObjectURL(new Blob([text], { type: `${mime};charset=utf-8` }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
