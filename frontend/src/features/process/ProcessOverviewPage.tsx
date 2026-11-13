import { Link } from "react-router-dom";
import { Search } from "lucide-react";
import { Card, CardHeader } from "../../components/ui/Card";
import { StatTile } from "../../components/ui/StatTile";
import { StatusChip } from "../../components/ui/StatusChip";
import { useAsync } from "../../lib/catalog/hooks";
import { getLineOverview, getLines } from "../../lib/process/api";
import {
  formatCount,
  formatNumber,
  formatPercent,
  formatRange,
  operationKindLabel,
  stepStatusLabel,
} from "../../lib/process/format";
import { filtersSearch, useProcessFilters } from "../../lib/process/useProcessFilters";
import type { StepOverview } from "../../lib/process/types";
import { ProcessFilterBar } from "./ProcessFilterBar";
import { ProcessFlow } from "./ProcessFlow";
import { StepNokTrendChart } from "./charts";

function nokRate(step: StepOverview): number | null {
  return step.has_specification ? step.spec_nok_rate : step.machine_nok_rate;
}

export function ProcessOverviewPage() {
  const [filters, setFilters] = useProcessFilters();
  const lines = useAsync(() => getLines(), []);
  const line = lines.data?.[0] ?? null;
  const overview = useAsync(
    () => (line ? getLineOverview(line.id, filters) : Promise.resolve(null)),
    [line?.id, filters],
  );
  const data = overview.data;
  const search = filtersSearch(filters);

  if (lines.loading) return <p className="text-sm text-text-secondary">Loading process…</p>;
  if (lines.error) return <p className="text-sm text-status-nok">{lines.error}</p>;
  if (!line) {
    return (
      <Card>
        <CardHeader title="No line data yet" />
        <p className="text-sm text-text-secondary">
          Load the line's station exports with the ingest tools (see backend/app/ingest/README.md) to see the process here.
        </p>
      </Card>
    );
  }

  // Steps with a partial record describe a sample of the pieces, so they stay
  // out of the line-level numbers (worst step, out-of-drawing count).
  const full = data?.steps.filter((s) => s.pieces > 0 && !s.partial_logging) ?? [];
  const worst = full.filter((s) => nokRate(s) !== null).sort((a, b) => (nokRate(b) ?? 0) - (nokRate(a) ?? 0))[0];
  const outOfDrawing = full.filter((s) => s.has_specification).reduce((sum, s) => sum + s.spec_nok, 0);
  const partialNames = data?.steps.filter((s) => s.pieces > 0 && s.partial_logging).map((s) => s.operation.name) ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Process · {line.name}</h1>
          <p className="text-sm text-text-secondary">
            {data ? formatRange(data.range.start, data.range.end) : "Loading range…"} · results per step, in line order
          </p>
        </div>
        <Link
          to="/process/pieces"
          className="inline-flex min-h-[44px] items-center gap-2 rounded border border-border px-3 text-sm font-medium text-text-primary hover:border-brand-primary"
        >
          <Search size={16} aria-hidden="true" /> Trace a piece
        </Link>
      </div>

      <ProcessFilterBar
        filters={filters}
        onChange={setFilters}
        range={data?.range ?? null}
        recipes={data?.recipes ?? []}
        busy={overview.loading && data !== null}
      />

      {overview.error && <p className="text-sm text-status-nok">{overview.error}</p>}
      {overview.loading && !data && <p className="text-sm text-text-secondary">Loading results…</p>}

      {data && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatTile label="Pieces at type check" value={formatCount(data.reference_pieces)} />
            <StatTile
              label={`Rolled yield · ${data.rolled_yield_steps} fully logged steps`}
              value={formatPercent(data.rolled_yield)}
            />
            <StatTile
              label={worst ? `Worst step · ${worst.operation.name}` : "Worst step"}
              value={worst ? `${formatPercent(nokRate(worst))} NOK` : "—"}
            />
            <StatTile label="Out-of-drawing step results" value={formatCount(outOfDrawing)} />
          </div>

          <Card>
            <CardHeader title="Process flow" />
            <ProcessFlow steps={data.steps} search={search} />
          </Card>

          <Card className="overflow-x-auto p-0">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Results per process step</caption>
              <thead className="sticky top-0 bg-surface">
                <tr className="border-b border-border text-xs text-text-secondary">
                  <th className="p-3 font-medium">#</th>
                  <th className="p-3 font-medium">Step</th>
                  <th className="p-3 text-right font-medium">Pieces</th>
                  <th className="p-3 text-right font-medium">Station NOK</th>
                  <th className="p-3 text-right font-medium">Out of drawing</th>
                  <th className="p-3 text-right font-medium">First pass</th>
                  <th className="p-3 text-right font-medium">Worst Cpk</th>
                  <th className="p-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {[...data.steps]
                  .sort((a, b) => a.operation.sequence - b.operation.sequence)
                  .map((step) => (
                    <tr key={step.operation.id} className="border-b border-border last:border-0 hover:bg-surface-app">
                      <td className="p-3 font-mono text-text-secondary">{String(step.operation.sequence).padStart(2, "0")}</td>
                      <td className="p-3">
                        <Link to={`/process/operations/${step.operation.id}${search}`} className="font-medium text-brand-primary hover:underline">
                          {step.operation.name}
                        </Link>
                        <p className="text-xs text-text-secondary">
                          {operationKindLabel(step.operation)}
                          {step.pieces > 0 && step.partial_logging && ` · logs ${formatPercent(step.coverage, 1)} of pieces`}
                        </p>
                      </td>
                      <td className="p-3 text-right font-mono">{formatCount(step.pieces)}</td>
                      <td className="p-3 text-right font-mono">{formatPercent(step.machine_nok_rate)}</td>
                      <td className="p-3 text-right font-mono">{step.has_specification ? formatPercent(step.spec_nok_rate) : "No spec"}</td>
                      <td className="p-3 text-right font-mono">{formatPercent(step.first_pass_yield, 1)}</td>
                      <td className="p-3 text-right font-mono">{formatNumber(step.worst_cpk, 2)}</td>
                      <td className="p-3">
                        <StatusChip status={step.status} label={stepStatusLabel(step)} />
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </Card>

          <Card>
            <CardHeader title="NOK rate per day, by step" />
            <StepNokTrendChart steps={full} />
            <p className="mt-2 text-xs text-text-secondary">
              Steps with a drawing tolerance use the drawing verdict; type check uses the station's own verdict.
              {partialNames.length > 0 &&
                ` Not drawn, because they log only part of the pieces: ${partialNames.join(", ")}.`}
            </p>
          </Card>
        </>
      )}
    </div>
  );
}
