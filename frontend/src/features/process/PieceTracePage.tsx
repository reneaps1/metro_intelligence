import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Search } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Card, CardHeader } from "../../components/ui/Card";
import { StatusChip, type ChipStatus } from "../../components/ui/StatusChip";
import { textInputClass } from "../../components/ui/FormField";
import { useAsync } from "../../lib/catalog/hooks";
import { getPieceTrace } from "../../lib/process/api";
import { formatLimits, operationKindLabel } from "../../lib/process/format";
import { formatDateTime } from "../../lib/format";

function verdict(ok: boolean | null): ChipStatus {
  if (ok === null) return "neutral";
  return ok ? "ok" : "nok";
}

export function PieceTracePage() {
  const { serial } = useParams();
  const navigate = useNavigate();
  const [query, setQuery] = useState(serial ?? "");
  const trace = useAsync(() => (serial ? getPieceTrace(serial) : Promise.resolve(null)), [serial]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const value = query.trim();
    if (value) navigate(`/process/pieces/${encodeURIComponent(value)}`);
  }

  return (
    <div className="space-y-4">
      <Link to="/process" className="inline-flex min-h-[44px] items-center gap-1 text-sm text-text-secondary hover:text-text-primary">
        <ArrowLeft size={16} aria-hidden="true" /> Process
      </Link>
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Piece trace</h1>
        <p className="text-sm text-text-secondary">Every step one piece went through, with each value and both verdicts.</p>
      </div>

      <Card>
        <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
          <label htmlFor="piece-serial" className="flex flex-col gap-1 text-sm text-text-secondary">
            Piece id
            <input
              id="piece-serial"
              className={`${textInputClass()} font-mono`}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. 2182702"
              inputMode="numeric"
              autoComplete="off"
            />
          </label>
          <Button type="submit" variant="primary">
            <Search size={16} aria-hidden="true" /> Trace
          </Button>
        </form>
      </Card>

      {serial && trace.loading && <p className="text-sm text-text-secondary">Loading piece…</p>}
      {serial && trace.error && (
        <p className="text-sm text-status-nok">
          {trace.error === "Piece not found." ? `No piece ${serial} in the loaded data.` : trace.error}
        </p>
      )}

      {trace.data && (
        <>
          <Card className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <div>
              <p className="text-xs text-text-secondary">Piece</p>
              <p className="font-mono text-lg font-semibold text-text-primary">{trace.data.serial_number}</p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">Recipe</p>
              <p className="text-sm text-text-primary">{trace.data.recipe?.label ?? "Not seen at type check"}</p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">Line</p>
              <p className="text-sm text-text-primary">{trace.data.line.name}</p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">First seen</p>
              <p className="text-sm text-text-primary">{formatDateTime(trace.data.first_seen_at)}</p>
            </div>
          </Card>

          <ol className="space-y-3" aria-label="Steps of this piece">
            {trace.data.steps.map((step) => (
              <li key={`${step.operation.id}-${step.attempt}`}>
                <Card className="p-0">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border p-4">
                    <div>
                      <p className="font-mono text-xs text-text-secondary">
                        {String(step.operation.sequence).padStart(2, "0")} · {formatDateTime(step.recorded_at)}
                        {step.nest !== null && ` · nest ${step.nest}`}
                        {step.attempt > 1 && ` · attempt ${step.attempt}`}
                      </p>
                      <p className="font-medium text-text-primary">{step.operation.name}</p>
                      <p className="text-xs text-text-secondary">{operationKindLabel(step.operation)}</p>
                    </div>
                    <StatusChip status={verdict(step.machine_ok)} label={`Station ${step.machine_ok === null ? "—" : step.machine_ok ? "OK" : "NOK"}`} />
                  </div>
                  {step.values.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm">
                        <caption className="sr-only">Values measured at {step.operation.name}</caption>
                        <thead>
                          <tr className="border-b border-border text-xs text-text-secondary">
                            <th className="p-3 font-medium">Characteristic</th>
                            <th className="p-3 text-right font-medium">Value</th>
                            <th className="p-3 font-medium">Drawing limits</th>
                            <th className="p-3 font-medium">Station</th>
                            <th className="p-3 font-medium">Drawing</th>
                          </tr>
                        </thead>
                        <tbody>
                          {step.values.map((v) => (
                            <tr key={v.characteristic_id} className="border-b border-border last:border-0">
                              <td className="p-3">
                                {v.name}
                                <span className="ml-2 font-mono text-xs text-text-secondary">{v.code}</span>
                              </td>
                              <td className="p-3 text-right font-mono">
                                {Number(v.value).toFixed(4)} {v.unit}
                              </td>
                              <td className="p-3 font-mono text-xs">{formatLimits(v.specification, v.unit)}</td>
                              <td className="p-3">
                                <StatusChip status={verdict(v.machine_ok)} label={v.machine_ok === null ? "—" : undefined} />
                              </td>
                              <td className="p-3">
                                <StatusChip status={verdict(v.is_ok)} label={v.is_ok === null ? "No spec" : undefined} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="p-4 text-sm text-text-secondary">Verdict only; this step records no values.</p>
                  )}
                </Card>
              </li>
            ))}
          </ol>
        </>
      )}

      {!serial && (
        <Card>
          <CardHeader title="Find a piece" />
          <p className="text-sm text-text-secondary">Enter the piece id printed on the part or shown in a station export.</p>
        </Card>
      )}
    </div>
  );
}
