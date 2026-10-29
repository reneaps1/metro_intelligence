import { useState } from "react";
import { Card, CardHeader } from "../../components/ui/Card";
import { Kpi } from "../../components/workbench/Kpi";
import { useAsync } from "../../lib/catalog/hooks";
import { useDemoSession } from "../../lib/demo/DemoSessionProvider";
import { fetchXyDetail } from "../../lib/quality-analytics/api";
import { formatPct } from "../../lib/quality-analytics/filters";
import type { QualityDataset, XYGroupBy } from "../../lib/quality-analytics/types";
import { GroupMeansChart, PinPositionChart, XY_MIN_GROUP_PIECES, signed, worstGroup } from "./PinPositionChart";

// IQ-F19: where the pin position drifts, against the drawing and end-of-line
// position tolerances. Same filters (and NOK basis) as steps 2-3. Descriptive
// only: the mean shift and the group means point engineering at where to
// look; they do not establish a cause.

const MARK_BY: { id: XYGroupBy; label: string }[] = [
  { id: "nok", label: "OK / NOK" },
  { id: "nest", label: "Nido" },
  { id: "mold_cavity", label: "Cavidad" },
];

const select =
  "ml-2 rounded-md border border-border bg-surface px-2 py-1 text-sm font-semibold normal-case tracking-normal text-text-primary";

export function PinPositionPanel({ dataset }: { dataset: QualityDataset }) {
  const pairs = dataset.pin_pairs ?? [];
  const { qualityFilters: f } = useDemoSession();
  const [pair, setPair] = useState(pairs[0]?.key ?? "");
  const [markBy, setMarkBy] = useState<XYGroupBy>("nok");
  const current = pairs.some((p) => p.key === pair) ? pair : (pairs[0]?.key ?? "");
  const offset = dataset.utc_offset_minutes ?? 0;
  const xy = useAsync(
    () => fetchXyDetail(f, current, markBy, offset),
    [JSON.stringify({ ...f, detailVariable: "", groupBy: "", granularity: "" }), current, markBy],
  );
  if (!pairs.length) return null;
  const d = xy.data;
  const options = MARK_BY.filter((m) => m.id !== "mold_cavity" || Boolean(dataset.available_filters.mold_cavity));
  const groupLabel = (g: number | string) => (markBy === "nest" ? `N${g}` : markBy === "mold_cavity" ? `C${g}` : String(g));
  const worst = d ? worstGroup(d) : null;
  const unit = d?.pair.unit ?? "mm";

  return (
    <Card className="space-y-3">
      <CardHeader
        title="Posición de pines X/Y vs. tolerancia"
        action={
          <div className="wb-seg" role="group" aria-label="Marcar por">
            {options.map((m) => (
              <button
                key={m.id}
                type="button"
                aria-pressed={markBy === m.id}
                onClick={() => setMarkBy(m.id)}
                className="!min-h-[26px] !px-2.5 !text-xs"
              >
                {m.label}
              </button>
            ))}
          </div>
        }
      />
      {pairs.length > 1 && (
        <label className="wb-label">
          Pin
          <select className={select} value={current} onChange={(e) => setPair(e.target.value)} aria-label="Pin a graficar">
            {pairs.map((p) => (
              <option key={p.key} value={p.key}>
                {p.label}
              </option>
            ))}
          </select>
        </label>
      )}
      {xy.error && (
        <p role="alert" className="text-sm text-status-nok">
          {xy.error}
        </p>
      )}
      {xy.loading && !d && <p className="text-sm text-text-secondary">Calculando…</p>}
      {d && d.pieces === 0 && <p className="text-sm text-text-secondary">No hay piezas con X e Y para la selección actual.</p>}
      {d && d.pieces > 0 && (
        <>
          <div className="wb-kpis" aria-label="Indicadores de posición">
            <Kpi size="sm" label="Piezas" value={d.pieces.toLocaleString("es-MX")} hint={`${d.nok_pieces.toLocaleString("es-MX")} NOK`} />
            {d.circles.map((c) => (
              <Kpi
                key={c.label}
                size="sm"
                label={`Fuera de ${c.label} Ø${c.diameter}`}
                value={formatPct(c.outside_rate, 1)}
                hint={`${c.outside.toLocaleString("es-MX")} piezas · TP > ${c.diameter} ${unit}`}
                tone={c.outside > 0 ? "nok" : undefined}
              />
            ))}
            {d.box_outside !== null && d.pair.tol_xy !== null && (
              <Kpi
                size="sm"
                label={`Fuera de ±${d.pair.tol_xy} en X o Y`}
                value={formatPct(d.box_outside_rate, 1)}
                hint={`${d.box_outside.toLocaleString("es-MX")} piezas`}
              />
            )}
            <Kpi
              size="sm"
              label="Posición verdadera (TP)"
              value={d.tp.median === null ? "—" : d.tp.median.toFixed(3)}
              hint={`mediana · p95 ${d.tp.p95?.toFixed(3) ?? "—"} · máx. ${d.tp.max?.toFixed(3) ?? "—"} ${unit}`}
            />
            {d.centroid && (
              <Kpi
                size="sm"
                label="Desplazamiento promedio"
                value={`${signed(d.centroid.dx)} / ${signed(d.centroid.dy)}`}
                hint={`ΔX / ΔY en ${unit} (flecha desde el nominal)`}
              />
            )}
          </div>
          {markBy === "nok" ? (
            <PinPositionChart detail={d} />
          ) : (
            <div className="grid items-start gap-4 xl:grid-cols-[3fr_2fr]">
              <PinPositionChart detail={d} />
              <div>
                <p className="wb-label mb-1">Promedio por {markBy === "nest" ? "nido" : "cavidad"} · ampliado</p>
                <GroupMeansChart detail={d} groupLabel={groupLabel} />
              </div>
            </div>
          )}
          <p className="text-xs text-text-secondary">
            Cada punto es una pieza: su desviación respecto al nominal ({d.pair.nominal_x}, {d.pair.nominal_y} {unit}). Círculos =
            zonas de posición (discontinuo: {d.circles[0]?.label ?? "—"}
            {d.circles.length > 1 ? `; punteado: ${d.circles.slice(1).map((c) => c.label).join(", ")}` : ""}); cuadro punteado = ±
            {d.pair.tol_xy ?? "—"} por eje. TP = 2·√(ΔX² + ΔY²). Triángulos = {d.nok_label}; rombo = su promedio; flecha =
            desplazamiento promedio de todas las piezas.
            {markBy !== "nok" &&
              ` A la derecha, ampliado: el promedio de cada ${markBy === "nest" ? "nido" : "cavidad"} (centro = nominal)${
                worst ? `; resaltado, ${groupLabel(worst.group)}, la mayor tasa NOK con al menos ${XY_MIN_GROUP_PIECES} piezas` : ""
              }.`}
            {d.points.length < d.points_total
              ? ` Se dibuja una muestra de ${d.points.length.toLocaleString("es-MX")} de ${d.points_total.toLocaleString("es-MX")} piezas (todas las NOK de la muestra se conservan); los indicadores usan todas.`
              : ""}{" "}
            Asociación, no causa.
          </p>
          {markBy !== "nok" && (
            <details className="text-xs">
              <summary className="cursor-pointer text-text-secondary">Ver tabla de promedios por {markBy === "nest" ? "nido" : "cavidad"}</summary>
              <table className="mt-2 w-full max-w-xl text-left font-mono" aria-label="Promedio de posición por grupo">
                <thead className="text-text-secondary">
                  <tr>
                    <th className="py-0.5 font-medium">Grupo</th>
                    <th className="py-0.5 text-right font-medium">Piezas</th>
                    <th className="py-0.5 text-right font-medium">NOK</th>
                    <th className="py-0.5 text-right font-medium">ΔX</th>
                    <th className="py-0.5 text-right font-medium">ΔY</th>
                  </tr>
                </thead>
                <tbody>
                  {d.groups.map((g) => (
                    <tr key={String(g.group)} className={g === worst ? "wb-nok font-semibold" : undefined}>
                      <td className="py-0.5">{groupLabel(g.group)}</td>
                      <td className="py-0.5 text-right">{g.pieces.toLocaleString("es-MX")}</td>
                      <td className="py-0.5 text-right">{g.nok.toLocaleString("es-MX")}</td>
                      <td className="py-0.5 text-right">{g.centroid ? signed(g.centroid.dx) : "—"}</td>
                      <td className="py-0.5 text-right">{g.centroid ? signed(g.centroid.dy) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          )}
        </>
      )}
    </Card>
  );
}
