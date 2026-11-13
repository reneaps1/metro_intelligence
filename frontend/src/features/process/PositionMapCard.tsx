import { useMemo, useState } from "react";
import clsx from "clsx";
import { Card, CardHeader } from "../../components/ui/Card";
import { StatTile } from "../../components/ui/StatTile";
import { useAsync } from "../../lib/catalog/hooks";
import { getPositionMap } from "../../lib/process/api";
import { formatCount, formatNumber, formatPercent } from "../../lib/process/format";
import type { NestPosition, PositionCell, PositionMap, ProcessFilters } from "../../lib/process/types";

// One-hue sequential scale (design-system.md): the accent at rising opacity
// over the surface, so it reads light-to-dark in both themes. Five classes on
// a log scale, because density spans several orders of magnitude.
const CLASS_OPACITY = [0.14, 0.3, 0.48, 0.68, 0.9];
const SIZE = 320;
const MARGIN = { top: 12, right: 16, bottom: 44, left: 52 };

type Hover = { kind: "cell"; cell: PositionCell } | { kind: "nest"; nest: NestPosition } | null;

function densityClass(count: number, max: number): number {
  if (max <= 1) return CLASS_OPACITY.length - 1;
  const position = Math.log(count) / Math.log(max);
  return Math.min(CLASS_OPACITY.length - 1, Math.floor(position * CLASS_OPACITY.length));
}

function classLowerBound(index: number, max: number): number {
  return Math.max(1, Math.ceil(Math.pow(max, index / CLASS_OPACITY.length)));
}

function outRate(stats: { pieces: number; out_of_tolerance: number }): number | null {
  return stats.pieces ? stats.out_of_tolerance / stats.pieces : null;
}

/** Where the X/Y position deviations of one pin land, against the drawing tolerance. */
export function PositionMapCard({ operationId, filters }: { operationId: string; filters: ProcessFilters }) {
  const [pin, setPin] = useState<number | null>(null);
  const map = useAsync(() => getPositionMap(operationId, pin, filters), [operationId, pin, filters]);
  const data = map.data;

  return (
    <Card>
      <CardHeader title="Pin position map · |ΔX| vs |ΔY|" />
      <p className="-mt-2 mb-3 text-sm text-text-secondary">
        Where each pin tip landed against the drawing tolerance. Darker cells hold more pieces; dots mark the median of each
        nest.
      </p>
      {data && (
        <div role="group" aria-label="Pin" className="mb-4 flex flex-wrap gap-1">
          {data.pins.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPin(p)}
              aria-pressed={data.pin === p}
              className={clsx(
                "min-h-[44px] min-w-[44px] rounded border px-3 text-sm font-medium",
                data.pin === p
                  ? "border-brand-primary bg-brand-primary text-text-on-brand"
                  : "border-border text-text-primary hover:bg-surface-app",
              )}
            >
              Pin {p}
            </button>
          ))}
        </div>
      )}
      {map.loading && <p className="text-sm text-text-secondary">Pairing X and Y values… this reads every piece in the range.</p>}
      {map.error && <p className="text-sm text-status-nok">{map.error}</p>}
      {data && !map.loading && <PositionMapBody data={data} />}
    </Card>
  );
}

function PositionMapBody({ data }: { data: PositionMap }) {
  const [hover, setHover] = useState<Hover>(null);
  const unit = data.unit ?? "";
  const total = data.total;
  const inside = total.pieces - total.out_of_tolerance;
  const nestsByRate = useMemo(
    () => [...data.nests].sort((a, b) => (outRate(b) ?? 0) - (outRate(a) ?? 0) || a.nest - b.nest),
    [data.nests],
  );

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label={`Pin ${data.pin} · pieces`} value={formatCount(total.pieces)} />
        <StatTile label="Inside drawing tolerance" value={formatPercent(total.pieces ? inside / total.pieces : null)} />
        <StatTile
          label={`Out of tolerance · X ${formatCount(total.out_x)} · Y ${formatCount(total.out_y)}`}
          value={formatCount(total.out_of_tolerance)}
        />
        <StatTile label="Beyond the shown range" value={formatCount(data.beyond_extent)} />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,420px)_1fr]">
        <div>
          <DensityMap data={data} onHover={setHover} />
          <HoverLine data={data} hover={hover} unit={unit} />
          <DensityLegend data={data} />
        </div>
        <div className="space-y-3">
          <p className="text-sm text-text-secondary">
            Median <span className="font-mono text-text-primary">|ΔX| {formatNumber(total.median_x)}</span> ·{" "}
            <span className="font-mono text-text-primary">|ΔY| {formatNumber(total.median_y)}</span> {unit}. 95 % of pins
            within <span className="font-mono text-text-primary">|ΔX| ≤ {formatNumber(total.p95_x)}</span> and{" "}
            <span className="font-mono text-text-primary">|ΔY| ≤ {formatNumber(total.p95_y)}</span> {unit}.
          </p>
          <NestTable nests={nestsByRate} unit={unit} />
          <p className="text-xs text-text-secondary">
            Groups are the station nests, the physical fixture positions, not a statistical clustering: a nest whose dot sits
            near a limit places pins off-centre and is the first place to look.
          </p>
        </div>
      </div>
    </div>
  );
}

function DensityMap({ data, onHover }: { data: PositionMap; onHover: (hover: Hover) => void }) {
  const plot = SIZE;
  const cell = plot / data.bins;
  const scale = (value: number) => (Math.min(value, data.extent) / data.extent) * plot;
  const max = Math.max(1, ...data.cells.map((c) => c.count));
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * data.extent);
  const width = plot + MARGIN.left + MARGIN.right;
  const height = plot + MARGIN.top + MARGIN.bottom;
  const tolX = data.tolerance_x;
  const tolY = data.tolerance_y;
  const labels = nestLabels(data, scale, plot);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full max-w-[420px]"
      role="img"
      aria-label={`Density of pin ${data.pin} position deviations; ${formatCount(data.total.pieces)} pieces. The nest table lists the same data.`}
      onMouseLeave={() => onHover(null)}
    >
      <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
        <rect width={plot} height={plot} fill="var(--bg-surface-raised)" stroke="var(--border-default)" />
        {ticks.map((t) => (
          <g key={`grid-${t}`} stroke="var(--border-default)" strokeOpacity={0.5}>
            <line x1={scale(t)} x2={scale(t)} y1={0} y2={plot} />
            <line x1={0} x2={plot} y1={plot - scale(t)} y2={plot - scale(t)} />
          </g>
        ))}
        {data.cells.map((c) => (
          <rect
            key={`${c.ix}-${c.iy}`}
            x={c.ix * cell}
            y={plot - (c.iy + 1) * cell}
            width={cell}
            height={cell}
            fill="var(--brand-accent)"
            fillOpacity={CLASS_OPACITY[densityClass(c.count, max)]}
            onMouseEnter={() => onHover({ kind: "cell", cell: c })}
          />
        ))}
        {tolX !== null && tolY !== null && (
          <rect
            x={0}
            y={plot - scale(tolY)}
            width={scale(tolX)}
            height={scale(tolY)}
            fill="none"
            stroke="var(--status-nok)"
            strokeWidth={2}
            strokeDasharray="6 4"
          />
        )}
        {tolX !== null && tolY === null && (
          <line x1={scale(tolX)} x2={scale(tolX)} y1={0} y2={plot} stroke="var(--status-nok)" strokeWidth={2} strokeDasharray="6 4" />
        )}
        {tolY !== null && tolX === null && (
          <line x1={0} x2={plot} y1={plot - scale(tolY)} y2={plot - scale(tolY)} stroke="var(--status-nok)" strokeWidth={2} strokeDasharray="6 4" />
        )}
        {tolX !== null && tolY !== null && (
          <text x={scale(tolX) - 4} y={plot - scale(tolY) - 6} textAnchor="end" fontSize={11} fill="var(--text-secondary)">
            Drawing tolerance {formatNumber(tolX, 2)}
          </text>
        )}
        {data.nests.map((n) =>
          n.median_x === null || n.median_y === null ? null : (
            <g key={`nest-${n.nest}`} onMouseEnter={() => onHover({ kind: "nest", nest: n })}>
              <circle cx={scale(n.median_x)} cy={plot - scale(n.median_y)} r={10} fill="transparent" />
              <circle
                cx={scale(n.median_x)}
                cy={plot - scale(n.median_y)}
                r={5}
                fill="var(--text-primary)"
                stroke="var(--bg-surface)"
                strokeWidth={2}
              />
              {labels.has(n.nest) && (
                <text x={scale(n.median_x) + 9} y={labels.get(n.nest)} fontSize={11} fill="var(--text-primary)">
                  N{n.nest}
                </text>
              )}
            </g>
          ),
        )}
        {ticks.map((t) => (
          <g key={`tick-${t}`} fontSize={11} fill="var(--text-secondary)" className="font-mono">
            <text x={scale(t)} y={plot + 16} textAnchor="middle">
              {formatNumber(t, 2)}
            </text>
            <text x={-6} y={plot - scale(t) + 4} textAnchor="end">
              {formatNumber(t, 2)}
            </text>
          </g>
        ))}
        <text x={plot / 2} y={plot + 36} textAnchor="middle" fontSize={12} fill="var(--text-secondary)">
          |ΔX| {data.unit ?? ""}
        </text>
        <text transform={`translate(${-40},${plot / 2}) rotate(-90)`} textAnchor="middle" fontSize={12} fill="var(--text-secondary)">
          |ΔY| {data.unit ?? ""}
        </text>
      </g>
    </svg>
  );
}

/** Labels only the nests above the overall share out of tolerance (at most
 * five), nudged down so no two labels overlap. Returns nest -> label y. */
function nestLabels(data: PositionMap, scale: (v: number) => number, plot: number): Map<number, number> {
  const overall = outRate(data.total) ?? 0;
  const picked = data.nests
    .filter((n) => n.median_x !== null && n.median_y !== null && (outRate(n) ?? 0) > overall)
    .sort((a, b) => (outRate(b) ?? 0) - (outRate(a) ?? 0))
    .slice(0, 5);
  const placed: { x: number; y: number }[] = [];
  const out = new Map<number, number>();
  for (const n of picked) {
    const x = scale(n.median_x as number);
    let y = plot - scale(n.median_y as number) + 4;
    while (placed.some((p) => Math.abs(p.x - x) < 36 && Math.abs(p.y - y) < 13)) y += 13;
    placed.push({ x, y });
    out.set(n.nest, y);
  }
  return out;
}

function HoverLine({ data, hover, unit }: { data: PositionMap; hover: Hover; unit: string }) {
  const step = data.extent / data.bins;
  let text = "Hover a cell or a nest dot for its values.";
  if (hover?.kind === "cell") {
    const { ix, iy, count } = hover.cell;
    text = `|ΔX| ${formatNumber(ix * step)}–${formatNumber((ix + 1) * step)} · |ΔY| ${formatNumber(iy * step)}–${formatNumber((iy + 1) * step)} ${unit} · ${formatCount(count)} pieces`;
  } else if (hover?.kind === "nest") {
    const n = hover.nest;
    text = `Nest ${n.nest} · ${formatCount(n.pieces)} pieces · median |ΔX| ${formatNumber(n.median_x)} |ΔY| ${formatNumber(n.median_y)} ${unit} · out of tolerance ${formatCount(n.out_of_tolerance)} (${formatPercent(outRate(n))})`;
  }
  return (
    <p className="mt-1 min-h-[2.5rem] font-mono text-xs text-text-secondary" aria-live="polite">
      {text}
    </p>
  );
}

function DensityLegend({ data }: { data: PositionMap }) {
  const max = Math.max(1, ...data.cells.map((c) => c.count));
  return (
    <div className="flex flex-wrap items-center gap-3 text-xs text-text-secondary">
      <span>Pieces per cell</span>
      {CLASS_OPACITY.map((opacity, i) => (
        <span key={opacity} className="inline-flex items-center gap-1">
          <svg width="14" height="14" aria-hidden="true">
            <rect width="14" height="14" rx="2" fill="var(--brand-accent)" fillOpacity={opacity} />
          </svg>
          <span className="font-mono">≥{formatCount(classLowerBound(i, max))}</span>
        </span>
      ))}
      <span className="inline-flex items-center gap-1">
        <svg width="18" height="14" aria-hidden="true">
          <line x1="0" x2="18" y1="7" y2="7" stroke="var(--status-nok)" strokeWidth="2" strokeDasharray="4 3" />
        </svg>
        Drawing tolerance
      </span>
    </div>
  );
}

function NestTable({ nests, unit }: { nests: NestPosition[]; unit: string }) {
  const maxRate = Math.max(0.0001, ...nests.map((n) => outRate(n) ?? 0));
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Pin position by nest, sorted by share out of tolerance</caption>
        <thead>
          <tr className="border-b border-border text-xs text-text-secondary">
            <th className="p-2 font-medium">Nest</th>
            <th className="p-2 text-right font-medium">Pieces</th>
            <th className="p-2 text-right font-medium">Median |ΔX|{unit && ` (${unit})`}</th>
            <th className="p-2 text-right font-medium">Median |ΔY|{unit && ` (${unit})`}</th>
            <th className="p-2 text-right font-medium">Out of tolerance</th>
            <th className="w-1/4 p-2 font-medium">
              <span className="sr-only">Share out of tolerance</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {nests.map((n) => {
            const rate = outRate(n) ?? 0;
            return (
              <tr key={n.nest} className="border-b border-border last:border-0">
                <td className="p-2 font-mono">N{n.nest}</td>
                <td className="p-2 text-right font-mono">{formatCount(n.pieces)}</td>
                <td className="p-2 text-right font-mono">{formatNumber(n.median_x)}</td>
                <td className="p-2 text-right font-mono">{formatNumber(n.median_y)}</td>
                <td className={clsx("whitespace-nowrap p-2 text-right font-mono", n.out_of_tolerance > 0 && "text-status-nok")}>
                  {formatCount(n.out_of_tolerance)} · {formatPercent(rate)}
                </td>
                <td className="p-2">
                  <div className="h-2 rounded bg-surface-app" aria-hidden="true">
                    <div className="h-2 rounded bg-status-nok" style={{ width: `${(rate / maxRate) * 100}%` }} />
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
