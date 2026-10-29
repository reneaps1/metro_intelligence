import { WB, limitLine, refLine } from "../../lib/demo/chartTheme";
import type { XYCentroid, XYDetailResponse } from "../../lib/quality-analytics/types";

// IQ-F19: X/Y deviation of a pin from its nominal, inside its position
// tolerance zones. Equal axes (a circle must look round), so it is a plain
// SVG like the boxplot. Workbench language (design-system.md §4.3): pieces are
// neutral marks; only NOK pieces and the worst group take the muted NOK
// accent; tolerance zones are limits in the text color with an uppercase
// label (first zone dashed, the others dotted); the mean shift is an arrow
// from the nominal. Group means (nest / mold cavity) are a few hundredths of a
// millimetre apart, so they get their own zoomed chart (`GroupMeansChart`).

/** Groups with fewer pieces are drawn but never called "the worst" (same rule as the backend ranking). */
export const XY_MIN_GROUP_PIECES = 30;

const SIZE = 460;
const M = { left: 56, right: 16, top: 16, bottom: 44 };
const PLOT = SIZE - M.left - M.right;

export const signed = (v: number, digits = 3) =>
  `${v >= 0 ? "+" : "−"}${Math.abs(v).toLocaleString("es-MX", { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;

function niceStep(raw: number): number {
  const pow = 10 ** Math.floor(Math.log10(raw));
  const f = raw / pow;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * pow;
}

export function worstGroup(detail: XYDetailResponse) {
  if (detail.group_by === "nok") return null;
  const ranked = detail.groups.filter((g) => g.pieces >= XY_MIN_GROUP_PIECES && g.nok > 0);
  return ranked.reduce<(typeof ranked)[number] | null>(
    (best, g) => (best === null || g.nok / g.pieces > best.nok / best.pieces ? g : best),
    null,
  );
}

export function PinPositionChart({ detail }: { detail: XYDetailResponse }) {
  const { pair, circles, points } = detail;
  const zone = Math.max(0, ...circles.map((c) => c.diameter / 2), pair.tol_xy ?? 0);
  // Show the zones whole and most of the cloud; a far outlier is clipped at the edge, not allowed to shrink the zones.
  const spread = Math.max(0, ...points.map((p) => Math.max(Math.abs(p[0]), Math.abs(p[1]))));
  const extent = Math.max(zone, zone > 0 ? Math.min(spread, zone * 2.5) : spread) * 1.12 || 1;
  const sx = (v: number) => M.left + ((v + extent) / (2 * extent)) * PLOT;
  const sy = (v: number) => M.top + ((extent - v) / (2 * extent)) * PLOT;
  const r = (v: number) => (v / (2 * extent)) * PLOT;
  const step = niceStep(extent / 2.5);
  const ticks: number[] = [];
  for (let t = -Math.floor(extent / step) * step; t <= extent + 1e-12; t += step) ticks.push(Number(t.toFixed(10)));
  const digits = Math.max(0, -Math.floor(Math.log10(step)));
  const fmt = (v: number) => v.toLocaleString("es-MX", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  const tri = (x: number, y: number, s = 3.6) => `${x},${y - s} ${x + s},${y + s * 0.8} ${x - s},${y + s * 0.8}`;
  const arrow = (c: XYCentroid | null) => c !== null && Math.hypot(c.dx, c.dy) > extent * 0.004;

  return (
    <svg
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      className="mx-auto block w-full max-w-[560px]"
      role="img"
      aria-label={`Dispersión X/Y de ${pair.label} contra su tolerancia de posición`}
    >
      <defs>
        <clipPath id="xy-plot">
          <rect x={M.left} y={M.top} width={PLOT} height={PLOT} />
        </clipPath>
        <marker id="xy-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill={WB.ref} />
        </marker>
      </defs>

      {/* Grid and axes */}
      {ticks.map((t) => (
        <g key={t}>
          <line x1={sx(t)} x2={sx(t)} y1={M.top} y2={M.top + PLOT} stroke={WB.grid} strokeOpacity={t === 0 ? 1 : 0.35} />
          <line x1={M.left} x2={M.left + PLOT} y1={sy(t)} y2={sy(t)} stroke={WB.grid} strokeOpacity={t === 0 ? 1 : 0.35} />
          <text x={sx(t)} y={M.top + PLOT + 14} textAnchor="middle" fontSize={10} fill={WB.text}>
            {fmt(t)}
          </text>
          <text x={M.left - 6} y={sy(t) + 3} textAnchor="end" fontSize={10} fill={WB.text}>
            {fmt(t)}
          </text>
        </g>
      ))}
      <text x={M.left + PLOT / 2} y={SIZE - 8} textAnchor="middle" fontSize={11} fill={WB.text}>
        ΔX vs. nominal ({pair.unit})
      </text>
      <text
        x={14}
        y={M.top + PLOT / 2}
        textAnchor="middle"
        fontSize={11}
        fill={WB.text}
        transform={`rotate(-90 14 ${M.top + PLOT / 2})`}
      >
        ΔY vs. nominal ({pair.unit})
      </text>

      <g clipPath="url(#xy-plot)">
        {/* Pieces: neutral marks, NOK pieces on top as triangles in the NOK accent (as in the I-MR chart). */}
        {points
          .filter((p) => !p[3])
          .map((p, i) => (
            <circle key={`o${i}`} cx={sx(p[0])} cy={sy(p[1])} r={1.7} fill={WB.bar} fillOpacity={0.45} />
          ))}
        {points
          .filter((p) => p[3])
          .map((p, i) => (
            <polygon key={`n${i}`} points={tri(sx(p[0]), sy(p[1]))} fill={WB.nok} fillOpacity={0.85} />
          ))}

        {/* Per-axis tolerance box and position zones: limits in the text color. */}
        {pair.tol_xy !== null && (
          <rect
            x={sx(-pair.tol_xy)}
            y={sy(pair.tol_xy)}
            width={2 * r(pair.tol_xy)}
            height={2 * r(pair.tol_xy)}
            fill="none"
            {...refLine}
            strokeWidth={1}
            strokeOpacity={0.7}
          />
        )}
        {circles.map((c, i) => (
          <circle
            key={c.label}
            cx={sx(0)}
            cy={sy(0)}
            r={r(c.diameter / 2)}
            fill="none"
            {...(i === 0 ? limitLine : refLine)}
          />
        ))}

        {/* Mean shift: arrow from the nominal; NOK mean as an outlined diamond. */}
        {arrow(detail.centroid) && detail.centroid && (
          <line
            x1={sx(0)}
            y1={sy(0)}
            x2={sx(detail.centroid.dx)}
            y2={sy(detail.centroid.dy)}
            stroke={WB.ref}
            strokeWidth={2}
            markerEnd="url(#xy-arrow)"
          />
        )}
        <circle cx={sx(0)} cy={sy(0)} r={2.5} fill={WB.ref} />
        {detail.nok_centroid && (
          <g>
            <title>{`Promedio de las piezas NOK: ΔX ${signed(detail.nok_centroid.dx)} · ΔY ${signed(detail.nok_centroid.dy)} ${pair.unit}`}</title>
            <rect
              x={sx(detail.nok_centroid.dx) - 5}
              y={sy(detail.nok_centroid.dy) - 5}
              width={10}
              height={10}
              transform={`rotate(45 ${sx(detail.nok_centroid.dx)} ${sy(detail.nok_centroid.dy)})`}
              fill="var(--bg-surface)"
              stroke={WB.nok}
              strokeWidth={2}
            />
          </g>
        )}

      </g>

      {/* Zone labels outside the cloud: first above its circle, second below, the rest at the box corner. */}
      {circles.map((c, i) => {
        const rr = r(c.diameter / 2);
        const y = i === 0 ? sy(0) - rr - 5 : sy(0) + rr + 13;
        if (i > 1 || y < M.top + 8 || y > M.top + PLOT - 2) return null;
        return (
          <text key={c.label} x={sx(0)} y={y} textAnchor="middle" fontSize={10} fontWeight={700} fill={WB.ref}>
            {`${c.label} Ø${c.diameter}`.toUpperCase()}
          </text>
        );
      })}
    </svg>
  );
}

/** IQ-F19: mean deviation of each nest / mold cavity, zoomed to their own spread (nominal at the centre). */
export function GroupMeansChart({
  detail,
  groupLabel,
}: {
  detail: XYDetailResponse;
  groupLabel: (g: number | string) => string;
}) {
  const groups = detail.groups.filter((g) => g.centroid !== null);
  if (!groups.length) return null;
  const S = 340;
  const m = { left: 52, right: 14, top: 14, bottom: 40 };
  const plot = S - m.left - m.right;
  const spread = Math.max(...groups.map((g) => Math.max(Math.abs(g.centroid!.dx), Math.abs(g.centroid!.dy))));
  const extent = (spread || 0.001) * 1.25;
  const sx = (v: number) => m.left + ((v + extent) / (2 * extent)) * plot;
  const sy = (v: number) => m.top + ((extent - v) / (2 * extent)) * plot;
  const step = niceStep(extent / 2);
  const ticks: number[] = [];
  for (let t = -Math.floor(extent / step) * step; t <= extent + 1e-12; t += step) ticks.push(Number(t.toFixed(10)));
  const digits = Math.max(0, -Math.floor(Math.log10(step)));
  const fmt = (v: number) => v.toLocaleString("es-MX", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  const worst = worstGroup(detail);
  const unit = detail.pair.unit;
  // Means that coincide would print their labels on top of each other: stack them below one another.
  const placed: { x: number; y: number }[] = [];
  const labelY = new Map<number | string, number>();
  for (const g of [...groups].sort((a, b) => sy(a.centroid!.dy) - sy(b.centroid!.dy) || sx(a.centroid!.dx) - sx(b.centroid!.dx))) {
    const x = sx(g.centroid!.dx) + 6;
    let y = sy(g.centroid!.dy) + 3.5;
    while (placed.some((p) => Math.abs(p.x - x) < 26 && Math.abs(p.y - y) < 10)) y += 10;
    placed.push({ x, y });
    labelY.set(g.group, y);
  }
  return (
    <svg
      viewBox={`0 0 ${S} ${S}`}
      className="mx-auto block w-full max-w-[420px]"
      role="img"
      aria-label={`Promedio de posición por ${detail.group_by === "nest" ? "nido" : "cavidad"} (ampliado)`}
    >
      {ticks.map((t) => (
        <g key={t}>
          <line x1={sx(t)} x2={sx(t)} y1={m.top} y2={m.top + plot} stroke={WB.grid} strokeOpacity={t === 0 ? 1 : 0.35} />
          <line x1={m.left} x2={m.left + plot} y1={sy(t)} y2={sy(t)} stroke={WB.grid} strokeOpacity={t === 0 ? 1 : 0.35} />
          <text x={sx(t)} y={m.top + plot + 14} textAnchor="middle" fontSize={10} fill={WB.text}>
            {fmt(t)}
          </text>
          <text x={m.left - 6} y={sy(t) + 3} textAnchor="end" fontSize={10} fill={WB.text}>
            {fmt(t)}
          </text>
        </g>
      ))}
      <text x={m.left + plot / 2} y={S - 8} textAnchor="middle" fontSize={11} fill={WB.text}>
        ΔX promedio ({unit})
      </text>
      <text x={14} y={m.top + plot / 2} textAnchor="middle" fontSize={11} fill={WB.text} transform={`rotate(-90 14 ${m.top + plot / 2})`}>
        ΔY promedio ({unit})
      </text>
      <text x={sx(0) + 4} y={m.top + 10} fontSize={10} fontWeight={700} fill={WB.ref}>
        NOMINAL
      </text>
      {groups.map((g) => {
        const c = g.centroid!;
        const isWorst = g === worst;
        return (
          <g key={String(g.group)} data-testid="xy-group">
            <title>{`${groupLabel(g.group)}: ${g.nok} NOK / ${g.pieces} piezas · promedio ΔX ${signed(c.dx)} · ΔY ${signed(c.dy)} ${unit}`}</title>
            <circle cx={sx(c.dx)} cy={sy(c.dy)} r={isWorst ? 4.5 : 3.5} fill={isWorst ? WB.nok : WB.mark} />
            <text
              x={sx(c.dx) + 6}
              y={labelY.get(g.group)}
              fontSize={9.5}
              fontWeight={isWorst ? 700 : 600}
              fill={isWorst ? WB.nok : WB.ref}
            >
              {groupLabel(g.group)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
