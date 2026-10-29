import { apiFetch } from "../api";
import type { QualityDataset } from "./types";

// IQ-F6: exploratory dimensional CSV import. Mirrors
// backend/app/schemas/quality_imports.py and app/api/v1/quality_imports.py.
// Large files are never rejected: only their head is sent (the backend says
// which share of the file was analysed).

export const PREVIEW_BYTES = 256 * 1024;
export const IMPORT_EXTENSIONS = [".csv", ".txt"];

export type Layout = "long" | "wide";
export type DateOrder = "ymd" | "dmy" | "mdy";
export type Delimiter = "," | ";" | "\t" | "|";
export type ColumnKind = "number" | "integer" | "datetime" | "text" | "empty";

/** Single-column roles; `value_columns` (wide layout) is separate. */
export type Role =
  | "timestamp"
  | "time"
  | "piece_id"
  | "group"
  | "cavity"
  | "machine"
  | "shift"
  | "batch"
  | "ok_nok"
  | "variable"
  | "value"
  | "nominal"
  | "lsl"
  | "usl"
  | "unit";

export interface ColumnProfile {
  name: string;
  kind: ColumnKind;
  non_empty: number;
  examples: string[];
}

export interface ImportPreview {
  encoding: string;
  delimiter: Delimiter;
  decimal: "." | ",";
  date_order: DateOrder;
  header: string[];
  rows: string[][];
  profiles: ColumnProfile[];
  suggestion: { layout: Layout; roles: Partial<Record<Role, string>>; value_columns: string[] };
  sampled_rows: number;
  limits: { max_bytes: number; max_rows: number };
}

export interface VariableSpecInput {
  nominal: number | null;
  lsl: number | null;
  usl: number | null;
  unit: string | null;
}

export interface ColumnMapping {
  layout: Layout;
  delimiter: Delimiter;
  decimal: "." | ",";
  date_order: DateOrder;
  roles: Partial<Record<Role, string>>;
  value_columns: string[];
  /** Keyed by value column (wide layout) */
  specs: Record<string, VariableSpecInput>;
}

export interface ImportReport {
  filename: string;
  layout: Layout;
  rows_read: number;
  rows_accepted: number;
  rows_quarantined: number;
  pieces: number;
  variables: number;
  empty_values: number;
  quarantine_by_reason: { reason: string; rows: number }[];
  quarantine_examples: { row_number: number; reason: string }[];
  warnings: string[];
  sample: { limited: boolean; rows_read: number; approx_file_pct: number | null; file_bytes: number; bytes_analysed: number };
}

export interface ImportedDatasetResponse {
  report: ImportReport;
  dataset: QualityDataset | null;
}

export interface RoleDef {
  role: Role;
  label: string;
  layouts: Layout[];
  required?: boolean;
  hint?: string;
}

export const ROLE_DEFS: RoleDef[] = [
  { role: "timestamp", label: "Fecha / hora", layouts: ["long", "wide"], required: true },
  { role: "time", label: "Hora (columna aparte)", layouts: ["long", "wide"] },
  { role: "piece_id", label: "ID de pieza", layouts: ["long", "wide"], hint: "Agrupa las filas de una misma pieza" },
  { role: "group", label: "ID de ciclo / disparo", layouts: ["long", "wide"] },
  { role: "cavity", label: "Nido / cavidad", layouts: ["long", "wide"], hint: "Se toma el número: «Nido 9», «CAV-09» → 9" },
  { role: "machine", label: "Máquina", layouts: ["long", "wide"] },
  { role: "shift", label: "Turno", layouts: ["long", "wide"] },
  { role: "batch", label: "Lote", layouts: ["long", "wide"] },
  { role: "ok_nok", label: "OK/NOK de la fuente", layouts: ["long", "wide"], hint: "Se muestra aparte del recalculado" },
  { role: "variable", label: "Variable (nombre)", layouts: ["long"], required: true },
  { role: "value", label: "Valor medido", layouts: ["long"], required: true },
  { role: "nominal", label: "Nominal", layouts: ["long"] },
  { role: "lsl", label: "Límite inferior (LIE)", layouts: ["long"] },
  { role: "usl", label: "Límite superior (LSE)", layouts: ["long"] },
  { role: "unit", label: "Unidad", layouts: ["long"] },
];

export function mappingFromPreview(p: ImportPreview): ColumnMapping {
  return {
    layout: p.suggestion.layout,
    delimiter: p.delimiter,
    decimal: p.decimal,
    date_order: p.date_order,
    roles: { ...p.suggestion.roles },
    value_columns: [...p.suggestion.value_columns],
    specs: {},
  };
}

/** Client-side mirror of ColumnMapping.validate() -- the backend re-checks. */
export function mappingErrors(m: ColumnMapping): string[] {
  const errors: string[] = [];
  const active = ROLE_DEFS.filter((d) => d.layouts.includes(m.layout));
  for (const def of active) {
    if (def.required && !m.roles[def.role]) errors.push(`Asigna la columna «${def.label}».`);
  }
  const used = active.map((d) => m.roles[d.role]).filter((c): c is string => Boolean(c));
  if (new Set(used).size !== used.length) errors.push("Una misma columna está asignada a dos campos.");
  if (m.layout === "wide") {
    if (!m.value_columns.length) errors.push("Elige al menos una columna de variable.");
    if (m.value_columns.some((c) => used.includes(c))) errors.push("Una columna de variable también está asignada a otro campo.");
    for (const [col, spec] of Object.entries(m.specs)) {
      if (m.value_columns.includes(col) && spec.lsl !== null && spec.usl !== null && spec.lsl > spec.usl) {
        errors.push(`«${col}»: el LIE es mayor que el LSE.`);
      }
    }
  }
  return errors;
}

/** Request body for POST /quality-analytics/datasets. Roles of the other layout are dropped. */
export function mappingPayload(m: ColumnMapping, name?: string): Record<string, unknown> {
  const roles = Object.fromEntries(
    ROLE_DEFS.filter((d) => d.layouts.includes(m.layout)).map((d) => [d.role, m.roles[d.role] || null]),
  );
  const specs =
    m.layout === "wide"
      ? Object.fromEntries(
          Object.entries(m.specs).filter(
            ([col, s]) => m.value_columns.includes(col) && (s.nominal !== null || s.lsl !== null || s.usl !== null || s.unit),
          ),
        )
      : {};
  return {
    layout: m.layout,
    delimiter: m.delimiter,
    decimal: m.decimal,
    date_order: m.date_order,
    ...roles,
    value_columns: m.layout === "wide" ? m.value_columns : [],
    specs,
    ...(name ? { name } : {}),
  };
}

/** "Muestra de X filas (~Y % del archivo)" -- null when the whole file was read. */
export function sampleNotice(report: ImportReport): string | null {
  const s = report.sample;
  if (!s.limited) return null;
  const pct =
    s.approx_file_pct === null
      ? ""
      : ` (~${s.approx_file_pct.toLocaleString("es-MX", { maximumFractionDigits: s.approx_file_pct < 10 ? 1 : 0 })} % del archivo)`;
  return `Muestra de ${s.rows_read.toLocaleString("es-MX")} filas${pct}. El análisis del archivo completo corresponde a un proceso por lotes fuera de la web.`;
}

export function parseOptionalNumber(raw: string): number | null {
  const s = raw.trim().replace(",", ".");
  if (!s) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

export function validateImportFile(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!IMPORT_EXTENSIONS.some((ext) => name.endsWith(ext))) return "Solo se aceptan archivos .csv o .txt.";
  if (file.size === 0) return "El archivo está vacío.";
  return null;
}

/** Exported for tests: what actually travels for a file of any size. */
export function uploadForm(file: File, bytes: number, extra: Record<string, string>): FormData {
  const body = new FormData();
  // Only the head of the file travels; the backend drops a cut last line.
  body.append("file", file.size > bytes ? file.slice(0, bytes, file.type) : file, file.name);
  body.append("file_size", String(file.size));
  for (const [key, value] of Object.entries(extra)) body.append(key, value);
  return body;
}

export function previewImport(file: File, delimiter?: Delimiter): Promise<ImportPreview> {
  return apiFetch<ImportPreview>("/quality-analytics/imports/preview", {
    method: "POST",
    body: uploadForm(file, PREVIEW_BYTES, delimiter ? { delimiter } : {}),
  });
}

export function createImportedDataset(file: File, mapping: ColumnMapping, maxBytes: number): Promise<ImportedDatasetResponse> {
  return apiFetch<ImportedDatasetResponse>("/quality-analytics/datasets", {
    method: "POST",
    body: uploadForm(file, maxBytes, { mapping: JSON.stringify(mappingPayload(mapping)) }),
  });
}

export function deleteImportedDataset(id: string): Promise<void> {
  return apiFetch<void>(`/quality-analytics/datasets/${encodeURIComponent(id)}`, { method: "DELETE" });
}
