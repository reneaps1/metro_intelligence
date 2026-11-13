import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, ArrowLeft } from "lucide-react";
import clsx from "clsx";
import { Card, CardHeader } from "../../components/ui/Card";
import { StatTile } from "../../components/ui/StatTile";
import { StatusChip } from "../../components/ui/StatusChip";
import { useAsync } from "../../lib/catalog/hooks";
import { getCharacteristicDetail, getOperationSummary } from "../../lib/process/api";
import {
  STATUS_LABEL,
  formatCount,
  formatLimits,
  formatNumber,
  formatPercent,
  formatRange,
  operationKindLabel,
} from "../../lib/process/format";
import { filtersSearch, useProcessFilters } from "../../lib/process/useProcessFilters";
import type { BreakdownRow, CharacteristicSummary } from "../../lib/process/types";
import { ProcessFilterBar } from "./ProcessFilterBar";
import { DailyMeanChart, DailyPiecesChart, ValueHistogram } from "./charts";

export function OperationDetailPage() {
  const { operationId = "" } = useParams();
  const [filters, setFilters] = useProcessFilters();
  const summary = useAsync(() => getOperationSummary(operationId, filters), [operationId, filters]);
  const data = summary.data;
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    if (!data) return;
    if (!selected || !data.characteristics.some((c) => c.id === selected)) {
      const first = data.characteristics.find((c) => c.specification !== null) ?? data.characteristics[0];
      setSelected(first?.id ?? null);
    }
  }, [data, selected]);

  if (summary.loading && !data) return <p className="text-sm text-text-secondary">Loading step…</p>;
  if (summary.error) return <p className="text-sm text-status-nok">{summary.error}</p>;
  if (!data) return null;

  const hasSpec = data.characteristics.some((c) => c.specification !== null);
  const nok = hasSpec ? data.spec_nok : data.machine_nok;
  const selectedChar = data.characteristics.find((c) => c.id === selected) ?? null;
  const search = filtersSearch(filters);

  return (
    <div className="space-y-4">
      <Link to={`/process${search}`} className="inline-flex min-h-[44px] items-center gap-1 text-sm text-text-secondary hover:text-text-primary">
        <ArrowLeft size={16} aria-hidden="true" /> Process
      </Link>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-xs text-text-secondary">
            Step {String(data.operation.sequence).padStart(2, "0")} · {data.operation.code}
          </p>
          <h1 className="text-xl font-semibold text-text-primary">{data.operation.name}</h1>
          <p className="text-sm text-text-secondary">
            {operationKindLabel(data.operation)} · {formatRange(data.range.start, data.range.end)}
          </p>
        </div>
        <StatusChip status={data.status} label={STATUS_LABEL[data.status]} />
      </div>

      <ProcessFilterBar filters={filters} onChange={setFilters} range={data.range} recipes={[]} />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Pieces (first attempt)" value={formatCount(data.pieces)} />
        <StatTile label="Station NOK" value={`${formatCount(data.machine_nok)} · ${formatPercent(data.pieces ? data.machine_nok / data.pieces : null)}`} />
        <StatTile
          label="Out of drawing tolerance"
          value={hasSpec ? `${formatCount(data.spec_nok)} · ${formatPercent(data.pieces ? data.spec_nok / data.pieces : null)}` : "No spec"}
        />
        <StatTile label="Repeated attempts" value={formatCount(data.repeat_attempts)} />
      </div>

      {data.disagreements > 0 && (
        <Card className="flex items-start gap-3 border-status-warning">
          <AlertTriangle size={20} className="mt-0.5 shrink-0 text-status-warning" aria-hidden="true" />
          <div>
            <p className="font-medium text-text-primary">
              {formatCount(data.disagreements)} values passed the station but are outside the drawing tolerance
            </p>
            <p className="text-sm text-text-secondary">
              The station applied a wider limit than the drawing for part of this period. Both verdicts are kept;
              open a characteristic to see where it happened.
            </p>
          </div>
        </Card>
      )}

      <Card>
        <CardHeader title={hasSpec ? "Pieces per day · drawing verdict" : "Pieces per day · station verdict"} />
        <DailyPiecesChart trend={data.trend} useSpec={hasSpec} />
      </Card>

      <Card className="overflow-x-auto p-0">
        <div className="p-4 pb-0">
          <CardHeader title={`Characteristics (${data.characteristics.length})`} />
        </div>
        <CharacteristicTable rows={data.characteristics} selected={selected} onSelect={setSelected} />
      </Card>

      {selectedChar && <CharacteristicPanel operationId={operationId} characteristic={selectedChar} filters={filters} />}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <BreakdownCard title="By recipe" rows={data.by_recipe} useSpec={hasSpec} nok={nok} />
        <BreakdownCard title="By nest" rows={data.by_nest} useSpec={hasSpec} nok={nok} />
      </div>
    </div>
  );
}

function CharacteristicTable({
  rows,
  selected,
  onSelect,
}: {
  rows: CharacteristicSummary[];
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  if (rows.length === 0) {
    return <p className="p-4 text-sm text-text-secondary">This step records a verdict only, no measured values.</p>;
  }
  return (
    <table className="w-full text-left text-sm">
      <caption className="sr-only">Measured characteristics of this step</caption>
      <thead className="sticky top-0 bg-surface">
        <tr className="border-b border-border text-xs text-text-secondary">
          <th className="p-3 font-medium">Characteristic</th>
          <th className="p-3 text-right font-medium">n</th>
          <th className="p-3 text-right font-medium">Mean</th>
          <th className="p-3 text-right font-medium">Std dev</th>
          <th className="p-3 text-right font-medium">Min</th>
          <th className="p-3 text-right font-medium">Max</th>
          <th className="p-3 font-medium">Drawing limits</th>
          <th className="p-3 text-right font-medium">Capability</th>
          <th className="p-3 text-right font-medium">Out of drawing</th>
          <th className="p-3 text-right font-medium">Station NOK</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((c) => (
          <tr
            key={c.id}
            className={clsx(
              "border-b border-border last:border-0 hover:bg-surface-app",
              selected === c.id && "bg-surface-app",
            )}
          >
            <td className="p-3">
              <button
                type="button"
                onClick={() => onSelect(c.id)}
                aria-pressed={selected === c.id}
                className="min-h-[44px] text-left font-medium text-brand-primary hover:underline"
              >
                {c.name}
              </button>
              <p className="font-mono text-xs text-text-secondary">{c.code}</p>
            </td>
            <td className="p-3 text-right font-mono">{formatCount(c.n)}</td>
            <td className="p-3 text-right font-mono">{formatNumber(c.mean, 4)}</td>
            <td className="p-3 text-right font-mono">{formatNumber(c.std_dev, 4)}</td>
            <td className="p-3 text-right font-mono">{formatNumber(c.min)}</td>
            <td className="p-3 text-right font-mono">{formatNumber(c.max)}</td>
            <td className="p-3 font-mono text-xs">{formatLimits(c.specification, c.unit)}</td>
            <td className="p-3 text-right font-mono">
              {c.cpk === null ? "—" : `${c.capability_kind} ${c.cpk.toFixed(2)}`}
            </td>
            <td className={clsx("p-3 text-right font-mono", c.spec_nok > 0 && "text-status-nok")}>
              {c.specification ? formatCount(c.spec_nok) : "—"}
            </td>
            <td className="p-3 text-right font-mono">{formatCount(c.machine_nok)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function CharacteristicPanel({
  operationId,
  characteristic,
  filters,
}: {
  operationId: string;
  characteristic: CharacteristicSummary;
  filters: ReturnType<typeof useProcessFilters>[0];
}) {
  const detail = useAsync(
    () => getCharacteristicDetail(operationId, characteristic.id, filters),
    [operationId, characteristic.id, filters],
  );
  const data = detail.data;
  return (
    <Card>
      <CardHeader title={`${characteristic.name} · ${characteristic.code}`} />
      {detail.loading && !data && <p className="text-sm text-text-secondary">Loading values…</p>}
      {detail.error && <p className="text-sm text-status-nok">{detail.error}</p>}
      {data && (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <div>
            <p className="mb-2 text-sm font-medium text-text-primary">Distribution</p>
            <ValueHistogram bins={data.bins} spec={data.characteristic.specification} unit={characteristic.unit} />
            {(data.below_range > 0 || data.above_range > 0) && (
              <p className="mt-1 text-xs text-text-secondary">
                Not drawn: {formatCount(data.below_range)} below and {formatCount(data.above_range)} above the shown range (gross outliers).
              </p>
            )}
          </div>
          <div>
            <p className="mb-2 text-sm font-medium text-text-primary">Daily mean</p>
            <DailyMeanChart daily={data.daily} spec={data.characteristic.specification} unit={characteristic.unit} />
          </div>
        </div>
      )}
    </Card>
  );
}

function BreakdownCard({
  title,
  rows,
  useSpec,
  nok,
}: {
  title: string;
  rows: BreakdownRow[];
  useSpec: boolean;
  nok: number;
}) {
  const max = Math.max(1, ...rows.map((r) => (useSpec ? r.spec_nok : r.machine_nok) / Math.max(1, r.pieces)));
  return (
    <Card className="overflow-x-auto p-0">
      <div className="p-4 pb-0">
        <CardHeader title={title} />
      </div>
      <table className="w-full text-left text-sm">
        <caption className="sr-only">{title}</caption>
        <thead>
          <tr className="border-b border-border text-xs text-text-secondary">
            <th className="p-3 font-medium">{title.replace("By ", "").replace(/^./, (c) => c.toUpperCase())}</th>
            <th className="p-3 text-right font-medium">Pieces</th>
            <th className="p-3 text-right font-medium">{useSpec ? "Out of drawing" : "Station NOK"}</th>
            <th className="w-1/3 p-3 font-medium">
              <span className="sr-only">Share of NOK</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const count = useSpec ? row.spec_nok : row.machine_nok;
            const rate = row.pieces ? count / row.pieces : 0;
            return (
              <tr key={row.key} className="border-b border-border last:border-0">
                <td className="p-3">{row.label}</td>
                <td className="p-3 text-right font-mono">{formatCount(row.pieces)}</td>
                <td className="p-3 text-right font-mono">
                  {formatCount(count)} · {formatPercent(rate)}
                </td>
                <td className="p-3">
                  <div className="h-2 rounded bg-surface-app" aria-hidden="true">
                    <div className="h-2 rounded bg-status-nok" style={{ width: `${(rate / max) * 100}%` }} />
                  </div>
                </td>
              </tr>
            );
          })}
          {rows.length === 0 && (
            <tr>
              <td colSpan={4} className="p-3 text-sm text-text-secondary">
                No pieces in this range.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <p className="px-4 pb-3 text-xs text-text-secondary">{formatCount(nok)} NOK pieces in total.</p>
    </Card>
  );
}
