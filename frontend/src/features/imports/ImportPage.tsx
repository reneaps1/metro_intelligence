import { Fragment, useRef, useState, type DragEvent } from "react";
import { UploadCloud } from "lucide-react";
import { useAuth } from "../../lib/auth/AuthProvider";
import { ApiError } from "../../lib/api";
import { uploadImport, validateFileClientSide } from "../../lib/imports/api";
import type { ImportedFile, ParseStatus } from "../../lib/imports/types";
import { Card, CardHeader } from "../../components/ui/Card";
import { StatusChip } from "../../components/ui/StatusChip";
import { formatDateTime } from "../../lib/format";

const STATUS_CHIP: Record<ParseStatus, { status: "ok" | "nok" | "warning" | "info"; label: string }> = {
  parsing: { status: "info", label: "Parsing…" },
  parsed: { status: "ok", label: "Parsed" },
  quarantined: { status: "warning", label: "Quarantined" },
  error: { status: "nok", label: "Error" },
};

export function ImportPage() {
  const { user } = useAuth();
  const canImport = user?.role === "metrologist" || user?.role === "admin";

  // Session-local: F4.5 exposes upload + get-by-id, not a list-all-imports
  // endpoint, so (same as F5.M's mock) history only covers what this browser
  // session has actually uploaded.
  const [history, setHistory] = useState<ImportedFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    const clientError = validateFileClientSide(file);
    if (clientError) {
      setUploadError(clientError);
      return;
    }
    setUploading(true);
    setUploadError(null);
    try {
      const result = await uploadImport(file);
      setHistory((h) => [result, ...h]);
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Unable to upload the file. Please try again.");
    } finally {
      setUploading(false);
    }
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragActive(false);
    if (!canImport || uploading) return;
    const file = event.dataTransfer.files[0];
    if (file) void handleFile(file);
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Import measurement file</h1>
        <p className="text-sm text-text-secondary">
          Every upload is validated before it reaches the catalog (CLAUDE.md §5); malformed rows are quarantined,
          never silently accepted.
        </p>
        {!canImport && (
          <p className="mt-2 text-xs text-text-disabled">
            Signed in as {user?.role.replace("_", " ")} — only Metrologist or Admin roles can upload files.
          </p>
        )}
      </div>

      <Card>
        <CardHeader title="Upload a file" />
        <div
          role="button"
          tabIndex={canImport ? 0 : -1}
          aria-disabled={!canImport}
          onClick={() => canImport && !uploading && inputRef.current?.click()}
          onKeyDown={(e) => {
            if ((e.key === "Enter" || e.key === " ") && canImport && !uploading) inputRef.current?.click();
          }}
          onDragOver={(e) => {
            e.preventDefault();
            if (canImport) setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          className={`flex min-h-[160px] flex-col items-center justify-center gap-2 rounded border-2 border-dashed p-6 text-center transition-colors ${
            !canImport
              ? "cursor-not-allowed border-border opacity-60"
              : dragActive
                ? "cursor-pointer border-brand-primary bg-status-info-bg"
                : "cursor-pointer border-border hover:border-brand-primary"
          }`}
        >
          <UploadCloud size={28} className="text-status-info" aria-hidden="true" />
          {uploading ? (
            <p className="text-sm text-text-secondary">Uploading…</p>
          ) : (
            <>
              <p className="text-sm text-text-primary">Drag and drop a CSV or XLSX file here, or click to browse</p>
              <p className="text-xs text-text-secondary">Max 20 MB — .csv, .xlsx</p>
            </>
          )}
          <input
            ref={inputRef}
            type="file"
            accept=".csv,.xlsx"
            className="sr-only"
            disabled={!canImport || uploading}
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file) void handleFile(file);
            }}
          />
        </div>
        {uploadError && (
          <p role="alert" className="mt-3 rounded bg-status-nok-bg px-3 py-2 text-sm text-status-nok">
            {uploadError}
          </p>
        )}
      </Card>

      <Card>
        <CardHeader title="Import history" />
        {history.length === 0 ? (
          <p className="text-sm text-text-secondary">No files uploaded yet in this session.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-text-secondary">
                <th className="p-2 font-medium">File</th>
                <th className="p-2 font-medium">Uploaded</th>
                <th className="p-2 font-medium">SHA-256</th>
                <th className="p-2 font-medium">Status</th>
                <th className="p-2 font-medium">Results</th>
                <th className="p-2" />
              </tr>
            </thead>
            <tbody>
              {history.map((file) => {
                const chip = STATUS_CHIP[file.parse_status];
                const hasQuarantine = file.quarantined_rows.length > 0;
                const expanded = expandedId === file.id;
                return (
                  <Fragment key={file.id}>
                    <tr className="border-b border-border last:border-0">
                      <td className="p-2 font-mono text-xs">{file.original_filename}</td>
                      <td className="p-2 text-xs text-text-secondary">{formatDateTime(file.created_at)}</td>
                      <td className="p-2 font-mono text-xs text-text-secondary" title={file.sha256}>
                        {file.sha256.slice(0, 12)}…
                      </td>
                      <td className="p-2">
                        <StatusChip status={chip.status} label={chip.label} />
                        {file.parse_status === "error" && file.error_detail && (
                          <p className="mt-1 max-w-xs text-xs text-status-nok">{file.error_detail}</p>
                        )}
                      </td>
                      <td className="p-2 text-xs text-text-secondary">
                        {file.runs_created} runs · {file.results_created} results
                        {hasQuarantine && `, ${file.quarantined_rows.length} quarantined`}
                      </td>
                      <td className="p-2 text-right">
                        {hasQuarantine && (
                          <button
                            type="button"
                            onClick={() => setExpandedId(expanded ? null : file.id)}
                            className="min-h-[44px] text-sm font-medium text-brand-primary hover:underline"
                          >
                            {expanded ? "Hide" : "View"} quarantined rows
                          </button>
                        )}
                      </td>
                    </tr>
                    {expanded && hasQuarantine && (
                      <tr className="border-b border-border last:border-0 bg-surface-app">
                        <td colSpan={6} className="p-3">
                          <table className="w-full text-left text-xs">
                            <thead>
                              <tr className="text-text-secondary">
                                <th className="p-2 font-medium">Row</th>
                                <th className="p-2 font-medium">Reason</th>
                              </tr>
                            </thead>
                            <tbody>
                              {file.quarantined_rows.map((row) => (
                                <tr key={row.id} className="border-t border-border">
                                  <td className="p-2 font-mono">{row.row_number}</td>
                                  <td className="p-2 text-status-warning">{row.reason}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
