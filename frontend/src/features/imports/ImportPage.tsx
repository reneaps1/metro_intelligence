import { UploadCloud } from "lucide-react";
import { Link } from "react-router-dom";
import { useDemoData } from "../../lib/mock/DataProvider";
import { useAuth } from "../../lib/auth/AuthProvider";
import { Card, CardHeader } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { StatusChip } from "../../components/ui/StatusChip";
import { formatDateTime } from "../../lib/format";
import type { ParseStatus } from "../../lib/mock/types";

const STATUS_CHIP: Record<ParseStatus, { status: "ok" | "nok" | "warning" | "info"; label: string }> = {
  pending: { status: "info", label: "Pending" },
  parsing: { status: "info", label: "Parsing…" },
  parsed: { status: "ok", label: "Parsed" },
  quarantined: { status: "warning", label: "Quarantined" },
  error: { status: "nok", label: "Error" },
};

export function ImportPage() {
  const { importScenarios, importedFiles, parts, importFile } = useDemoData();
  const { user } = useAuth();
  const canImport = user?.role === "metrologist" || user?.role === "admin";

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Import measurement file</h1>
        <p className="text-sm text-text-secondary">
          Demo upload — pick one of the sample files below instead of a real file picker. Every upload is validated
          before it reaches the catalog (CLAUDE.md §5); malformed files are quarantined, not silently accepted.
        </p>
        {!canImport && (
          <p className="mt-2 text-xs text-text-disabled">
            Signed in as {user?.role.replace("_", " ")} — only Metrologist or Admin roles can upload files.
          </p>
        )}
      </div>

      <Card>
        <CardHeader title="Sample files" />
        <div className="space-y-3">
          {importScenarios.map((scenario) => (
            <div key={scenario.id} className="flex items-center justify-between gap-4 rounded border border-border p-3">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded bg-status-info-bg text-status-info">
                  <UploadCloud size={18} />
                </span>
                <div>
                  <p className="font-mono text-xs text-text-secondary">{scenario.filename}</p>
                  <p className="text-sm text-text-primary">{scenario.description}</p>
                </div>
              </div>
              <Button variant="secondary" onClick={() => importFile(scenario.id)} disabled={!canImport} title={canImport ? undefined : "Only Metrologist or Admin roles can import files"}>
                Upload
              </Button>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <CardHeader title="Import history" />
        {importedFiles.length === 0 ? (
          <p className="text-sm text-text-secondary">No files uploaded yet in this session.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-text-secondary">
                <th className="p-2 font-medium">File</th>
                <th className="p-2 font-medium">Uploaded</th>
                <th className="p-2 font-medium">SHA-256</th>
                <th className="p-2 font-medium">Status</th>
                <th className="p-2" />
              </tr>
            </thead>
            <tbody>
              {importedFiles.map((file) => {
                const chip = STATUS_CHIP[file.status];
                const part = parts.find((p) => p.id === file.partId);
                return (
                  <tr key={file.id} className="border-b border-border last:border-0">
                    <td className="p-2 font-mono text-xs">{file.filename}</td>
                    <td className="p-2 text-xs text-text-secondary">{formatDateTime(file.uploadedAt)}</td>
                    <td className="p-2 font-mono text-xs text-text-secondary" title={file.sha256}>
                      {file.sha256.slice(0, 12)}…
                    </td>
                    <td className="p-2">
                      <StatusChip status={chip.status} label={chip.label} />
                      {file.status === "quarantined" && file.errorDetail && (
                        <p className="mt-1 max-w-xs text-xs text-status-warning">{file.errorDetail}</p>
                      )}
                    </td>
                    <td className="p-2 text-right">
                      {file.status === "parsed" && part && (
                        <Link to={`/catalog/${part.id}`} className="text-sm font-medium text-brand-primary hover:underline">
                          View {part.code}
                        </Link>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
