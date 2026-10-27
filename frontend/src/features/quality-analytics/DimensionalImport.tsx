import { useRef, useState, type DragEvent } from "react";
import { AlertTriangle, FileSpreadsheet, UploadCloud } from "lucide-react";
import clsx from "clsx";
import { ApiError } from "../../lib/api";
import {
  ROLE_DEFS,
  createImportedDataset,
  mappingErrors,
  mappingFromPreview,
  parseOptionalNumber,
  previewImport,
  sampleNotice,
  validateImportFile,
  type ColumnKind,
  type ColumnMapping,
  type DateOrder,
  type Delimiter,
  type ImportPreview,
  type ImportReport,
  type Layout,
  type Role,
  type VariableSpecInput,
} from "../../lib/quality-analytics/imports";
import type { QualityDataset } from "../../lib/quality-analytics/types";

// IQ-F6: CSV -> column mapping -> validated dimensional dataset. Used by the
// import page (industrial edition) and inline in demo steps 2/3. Whatever
// happens here, the preloaded demo dataset is untouched.

const DELIMITERS: { id: Delimiter; label: string }[] = [
  { id: ",", label: "Coma (,)" },
  { id: ";", label: "Punto y coma (;)" },
  { id: "\t", label: "Tabulador" },
  { id: "|", label: "Barra (|)" },
];
const DATE_ORDERS: { id: DateOrder; label: string }[] = [
  { id: "dmy", label: "Día/Mes/Año" },
  { id: "mdy", label: "Mes/Día/Año" },
  { id: "ymd", label: "Año-Mes-Día" },
];
const KIND_LABEL: Record<ColumnKind, string> = {
  number: "número",
  integer: "entero",
  datetime: "fecha",
  text: "texto",
  empty: "vacía",
};
const EMPTY_SPEC: VariableSpecInput = { nominal: null, lsl: null, usl: null, unit: null };
const mb = (bytes: number) => `${(bytes / (1024 * 1024)).toLocaleString("es-MX", { maximumFractionDigits: 1 })} MB`;
const n = (v: number) => v.toLocaleString("es-MX");
const selectClass = "w-full rounded border border-border bg-surface px-2 py-1.5 text-sm text-text-primary";

function errorText(err: unknown): string {
  return err instanceof ApiError ? err.message : "No se pudo procesar el archivo. Intenta de nuevo.";
}

export function DimensionalImport({ onImported }: { onImported: (dataset: QualityDataset) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [mapping, setMapping] = useState<ColumnMapping | null>(null);
  const [report, setReport] = useState<ImportReport | null>(null);
  const [dataset, setDataset] = useState<QualityDataset | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function loadPreview(f: File, delimiter?: Delimiter) {
    const clientError = validateImportFile(f);
    if (clientError) {
      setError(clientError);
      return;
    }
    setBusy(true);
    setError(null);
    setReport(null);
    setDataset(null);
    try {
      const p = await previewImport(f, delimiter);
      setFile(f);
      setPreview(p);
      setMapping(mappingFromPreview(p));
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function analyse() {
    if (!file || !preview || !mapping) return;
    setBusy(true);
    setError(null);
    try {
      const result = await createImportedDataset(file, mapping, preview.limits.max_bytes);
      setReport(result.report);
      setDataset(result.dataset);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setFile(null);
    setPreview(null);
    setMapping(null);
    setReport(null);
    setDataset(null);
    setError(null);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragActive(false);
    const f = event.dataTransfer.files[0];
    if (f && !busy) void loadPreview(f);
  }

  return (
    <div className="space-y-4">
      {error && (
        <p role="alert" className="rounded bg-status-nok-bg px-3 py-2 text-sm text-status-nok">
          {error}
        </p>
      )}

      {!preview && (
        <div
          role="button"
          tabIndex={0}
          aria-label="Elegir archivo CSV"
          onClick={() => !busy && inputRef.current?.click()}
          onKeyDown={(e) => {
            if ((e.key === "Enter" || e.key === " ") && !busy) inputRef.current?.click();
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          className={clsx(
            "flex min-h-[140px] cursor-pointer flex-col items-center justify-center gap-2 rounded border-2 border-dashed p-6 text-center",
            dragActive ? "border-brand-primary bg-status-info-bg" : "border-border hover:border-brand-primary",
          )}
        >
          <UploadCloud size={28} className="text-status-info" aria-hidden="true" />
          <p className="text-sm text-text-primary">
            {busy ? "Leyendo el archivo…" : "Arrastra un CSV de mediciones dimensionales o haz clic para elegirlo"}
          </p>
          <p className="text-xs text-text-secondary">
            Formato largo (una fila por medición) o ancho (una fila por pieza). Los archivos grandes se analizan por muestra.
            Ejemplos ficticios: <code>seed/sample_files/mi_demo_dimensional_long.csv</code> y <code>_wide.csv</code>.
          </p>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,.txt,text/csv"
            className="sr-only"
            data-testid="dimensional-file-input"
            onChange={(e) => {
              const f = e.target.files?.[0];
              e.target.value = "";
              if (f) void loadPreview(f);
            }}
          />
        </div>
      )}

      {preview && mapping && file && !report && (
        <MappingEditor
          file={file}
          preview={preview}
          mapping={mapping}
          setMapping={setMapping}
          busy={busy}
          onDelimiter={(d) => void loadPreview(file, d)}
          onAnalyse={() => void analyse()}
          onCancel={reset}
        />
      )}

      {report && (
        <ImportResult
          report={report}
          dataset={dataset}
          onUse={() => dataset && onImported(dataset)}
          onAdjust={() => {
            setReport(null);
            setDataset(null);
          }}
          onAnother={reset}
        />
      )}
    </div>
  );
}

function MappingEditor({
  file,
  preview,
  mapping,
  setMapping,
  busy,
  onDelimiter,
  onAnalyse,
  onCancel,
}: {
  file: File;
  preview: ImportPreview;
  mapping: ColumnMapping;
  setMapping: (m: ColumnMapping) => void;
  busy: boolean;
  onDelimiter: (d: Delimiter) => void;
  onAnalyse: () => void;
  onCancel: () => void;
}) {
  const errors = mappingErrors(mapping);
  const kind = Object.fromEntries(preview.profiles.map((p) => [p.name, p.kind]));
  const roles = ROLE_DEFS.filter((d) => d.layouts.includes(mapping.layout));
  const roleOf = (col: string) => roles.find((d) => mapping.roles[d.role] === col)?.label;
  const setRole = (role: Role, col: string) =>
    setMapping({
      ...mapping,
      roles: { ...mapping.roles, [role]: col || undefined },
      value_columns: mapping.value_columns.filter((c) => c !== col),
    });
  const setSpec = (col: string, field: keyof VariableSpecInput, raw: string) => {
    const prev = mapping.specs[col] ?? EMPTY_SPEC;
    const value = field === "unit" ? raw.trim() || null : parseOptionalNumber(raw);
    setMapping({ ...mapping, specs: { ...mapping.specs, [col]: { ...prev, [field]: value } } });
  };
  const candidateColumns = preview.header.filter((c) => !roles.some((d) => mapping.roles[d.role] === c));
  const willSample = file.size > preview.limits.max_bytes;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        <span className="inline-flex items-center gap-1 font-medium text-text-primary">
          <FileSpreadsheet size={16} aria-hidden="true" /> {file.name}
        </span>
        <span className="text-text-secondary">
          {mb(file.size)} · codificación {preview.encoding} · {preview.header.length} columnas
        </span>
        <label className="text-xs font-semibold text-text-secondary">
          Delimitador
          <select
            className="ml-2 rounded border border-border bg-surface px-2 py-1 text-sm text-text-primary"
            value={mapping.delimiter}
            disabled={busy}
            onChange={(e) => onDelimiter(e.target.value as Delimiter)}
          >
            {DELIMITERS.map((d) => (
              <option key={d.id} value={d.id}>
                {d.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-semibold text-text-secondary">
          Decimal
          <select
            className="ml-2 rounded border border-border bg-surface px-2 py-1 text-sm text-text-primary"
            value={mapping.decimal}
            onChange={(e) => setMapping({ ...mapping, decimal: e.target.value as "." | "," })}
          >
            <option value=".">Punto (1.25)</option>
            <option value=",">Coma (1,25)</option>
          </select>
        </label>
        <label className="text-xs font-semibold text-text-secondary">
          Fechas
          <select
            className="ml-2 rounded border border-border bg-surface px-2 py-1 text-sm text-text-primary"
            value={mapping.date_order}
            onChange={(e) => setMapping({ ...mapping, date_order: e.target.value as DateOrder })}
          >
            {DATE_ORDERS.map((d) => (
              <option key={d.id} value={d.id}>
                {d.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {willSample && (
        <p className="flex items-start gap-2 rounded bg-status-warning-bg px-3 py-2 text-sm text-status-warning">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
          Archivo grande: se analizará una muestra del inicio (hasta {mb(preview.limits.max_bytes)} y{" "}
          {n(preview.limits.max_rows)} filas) de {mb(file.size)}.
        </p>
      )}

      <fieldset>
        <legend className="mb-1 text-xs font-semibold text-text-secondary">Formato del archivo</legend>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Formato del archivo">
          {(
            [
              ["long", "Largo · una fila por medición"],
              ["wide", "Ancho · una fila por pieza"],
            ] as [Layout, string][]
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              aria-pressed={mapping.layout === id}
              onClick={() => setMapping({ ...mapping, layout: id })}
              className={clsx(
                "rounded border px-3 py-1.5 text-sm",
                mapping.layout === id
                  ? "border-brand-primary bg-brand-primary text-text-on-brand"
                  : "border-border bg-surface text-text-secondary",
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </fieldset>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Mapeo de columnas">
        {roles.map((def) => (
          <label key={def.role} className="text-xs font-semibold text-text-secondary">
            {def.label}
            {def.required && <span className="text-status-nok"> *</span>}
            <select
              className={clsx(selectClass, "mt-1")}
              value={mapping.roles[def.role] ?? ""}
              onChange={(e) => setRole(def.role, e.target.value)}
              aria-label={def.label}
            >
              <option value="">— sin asignar —</option>
              {preview.header.map((col) => (
                <option key={col} value={col}>
                  {col} ({KIND_LABEL[kind[col] as ColumnKind]})
                </option>
              ))}
            </select>
            {def.hint && <span className="mt-0.5 block font-normal">{def.hint}</span>}
          </label>
        ))}
      </div>

      {mapping.layout === "wide" && (
        <WideVariables preview={preview} mapping={mapping} candidates={candidateColumns} setMapping={setMapping} setSpec={setSpec} />
      )}
      {mapping.layout === "long" && !mapping.roles.lsl && !mapping.roles.usl && (
        <p className="text-xs text-text-secondary">
          Sin columnas de límites: no habrá NOK por especificación ni Cp/Cpk (solo distribuciones y el OK/NOK de la fuente).
        </p>
      )}

      <div>
        <p className="mb-1 text-xs font-semibold text-text-secondary">
          Primeras {preview.rows.length} filas (de {n(preview.sampled_rows)} leídas para detectar tipos)
        </p>
        <div className="max-h-72 overflow-auto rounded border border-border">
          <table className="w-full text-left text-xs" aria-label="Vista previa del archivo">
            <thead className="sticky top-0 bg-surface-app">
              <tr>
                {preview.header.map((col) => {
                  const role = roleOf(col) ?? (mapping.layout === "wide" && mapping.value_columns.includes(col) ? "Variable" : null);
                  return (
                    <th key={col} className="whitespace-nowrap border-b border-border p-2 font-medium text-text-primary">
                      {col}
                      <span className={clsx("block font-normal", role ? "text-brand-primary" : "text-text-disabled")}>
                        {role ?? "ignorada"}
                      </span>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {preview.rows.map((row, i) => (
                <tr key={i} className="border-b border-border last:border-0">
                  {preview.header.map((col, j) => (
                    <td key={col} className="whitespace-nowrap p-2 font-mono text-text-secondary">
                      {row[j] ?? ""}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {errors.length > 0 && (
        <ul className="list-disc pl-5 text-sm text-status-warning" aria-label="Problemas del mapeo">
          {errors.map((e) => (
            <li key={e}>{e}</li>
          ))}
        </ul>
      )}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy || errors.length > 0}
          onClick={onAnalyse}
          className="rounded bg-brand-primary px-4 py-2 text-sm font-medium text-text-on-brand disabled:opacity-50"
        >
          {busy ? "Analizando…" : "Validar y analizar"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded border border-border px-4 py-2 text-sm text-text-secondary hover:border-brand-primary"
        >
          Cambiar archivo
        </button>
      </div>
    </div>
  );
}

function WideVariables({
  preview,
  mapping,
  candidates,
  setMapping,
  setSpec,
}: {
  preview: ImportPreview;
  mapping: ColumnMapping;
  candidates: string[];
  setMapping: (m: ColumnMapping) => void;
  setSpec: (col: string, field: keyof VariableSpecInput, raw: string) => void;
}) {
  const numeric = new Set(preview.profiles.filter((p) => p.kind === "number" || p.kind === "integer").map((p) => p.name));
  const toggle = (col: string) =>
    setMapping({
      ...mapping,
      value_columns: mapping.value_columns.includes(col)
        ? mapping.value_columns.filter((c) => c !== col)
        : [...mapping.value_columns, col],
    });
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold text-text-secondary">
        Columnas de variables dimensionales y su especificación (opcional; sin LIE/LSE no se calcula NOK ni Cp/Cpk)
      </p>
      <div className="overflow-x-auto rounded border border-border">
        <table className="w-full text-left text-sm" aria-label="Variables y tolerancias">
          <thead className="text-xs text-text-secondary">
            <tr className="border-b border-border">
              <th className="p-2 font-medium">Variable</th>
              <th className="p-2 font-medium">Nominal</th>
              <th className="p-2 font-medium">LIE</th>
              <th className="p-2 font-medium">LSE</th>
              <th className="p-2 font-medium">Unidad</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((col) => {
              const checked = mapping.value_columns.includes(col);
              return (
                <tr key={col} className="border-b border-border last:border-0">
                  <td className="p-2">
                    <label className="inline-flex items-center gap-2">
                      <input type="checkbox" checked={checked} onChange={() => toggle(col)} />
                      <span className={checked ? "text-text-primary" : "text-text-secondary"}>{col}</span>
                      {!numeric.has(col) && <span className="text-xs text-text-disabled">(no numérica)</span>}
                    </label>
                  </td>
                  {(["nominal", "lsl", "usl", "unit"] as const).map((field) => (
                    <td key={field} className="p-2">
                      <input
                        type="text"
                        inputMode={field === "unit" ? "text" : "decimal"}
                        disabled={!checked}
                        aria-label={`${field === "lsl" ? "LIE" : field === "usl" ? "LSE" : field === "unit" ? "Unidad" : "Nominal"} de ${col}`}
                        defaultValue={(() => {
                          const v = mapping.specs[col]?.[field];
                          return v === null || v === undefined ? "" : String(v);
                        })()}
                        onChange={(e) => setSpec(col, field, e.target.value)}
                        className="w-24 rounded border border-border bg-surface px-2 py-1 font-mono text-sm text-text-primary disabled:opacity-40"
                      />
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ImportResult({
  report,
  dataset,
  onUse,
  onAdjust,
  onAnother,
}: {
  report: ImportReport;
  dataset: QualityDataset | null;
  onUse: () => void;
  onAdjust: () => void;
  onAnother: () => void;
}) {
  const notice = sampleNotice(report);
  return (
    <div className="space-y-3" aria-label="Resultado de la importación">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {[
          ["Filas leídas", n(report.rows_read)],
          ["Aceptadas", n(report.rows_accepted)],
          ["En cuarentena", n(report.rows_quarantined)],
          ["Piezas", n(report.pieces)],
          ["Variables", n(report.variables)],
        ].map(([label, value]) => (
          <div key={label} className="rounded border border-border bg-surface p-3">
            <p className="text-xs text-text-secondary">{label}</p>
            <p className="font-mono text-lg font-semibold text-text-primary">{value}</p>
          </div>
        ))}
      </div>
      {notice && (
        <p className="rounded bg-status-warning-bg px-3 py-2 text-sm text-status-warning" role="status">
          {notice}
        </p>
      )}
      {report.warnings.length > 0 && (
        <ul className="list-disc pl-5 text-sm text-status-warning">
          {report.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}
      {report.quarantine_by_reason.length > 0 && (
        <details className="rounded border border-border p-3 text-sm">
          <summary className="cursor-pointer font-medium text-text-primary">
            Cuarentena: {n(report.rows_quarantined)} filas no se usaron (motivo y ejemplos)
          </summary>
          <table className="mt-2 w-full text-left text-xs">
            <tbody>
              {report.quarantine_by_reason.map((q) => (
                <tr key={q.reason} className="border-t border-border">
                  <td className="p-2 text-status-warning">{q.reason}</td>
                  <td className="p-2 text-right font-mono">{n(q.rows)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-text-secondary">
            Filas de ejemplo (número de fila de datos):{" "}
            {report.quarantine_examples
              .slice(0, 20)
              .map((e) => e.row_number)
              .join(", ")}
          </p>
        </details>
      )}
      {!dataset && (
        <p role="alert" className="rounded bg-status-nok-bg px-3 py-2 text-sm text-status-nok">
          Ninguna fila pasó la validación. Revisa el mapeo (columna de fecha, formato de fecha, decimal).
        </p>
      )}
      <p className="text-xs text-text-secondary">
        Análisis temporal: el archivo se procesa en memoria, solo para tu usuario, y no se guarda en el historial de
        mediciones ni en el almacenamiento de archivos.
      </p>
      <div className="flex flex-wrap gap-2">
        {dataset && (
          <button
            type="button"
            onClick={onUse}
            className="rounded bg-brand-primary px-4 py-2 text-sm font-medium text-text-on-brand"
          >
            Ver analíticas de este archivo
          </button>
        )}
        <button
          type="button"
          onClick={onAdjust}
          className="rounded border border-border px-4 py-2 text-sm text-text-secondary hover:border-brand-primary"
        >
          Ajustar mapeo
        </button>
        <button
          type="button"
          onClick={onAnother}
          className="rounded border border-border px-4 py-2 text-sm text-text-secondary hover:border-brand-primary"
        >
          Importar otro archivo
        </button>
      </div>
    </div>
  );
}
