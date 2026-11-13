import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { FlaskConical, Info } from "lucide-react";
import { Card, CardHeader } from "../../components/ui/Card";
import { OriginBadge } from "../../components/ui/OriginBadge";
import { Kpi } from "../../components/workbench/Kpi";
import { Notice } from "../../components/workbench/Notice";
import { WB, axisTick, gridProps, tooltipStyle } from "../../lib/demo/chartTheme";
import { useAsync } from "../../lib/catalog/hooks";
import { describeCorrelation, formatCoefficient } from "../../lib/industrial-signals/correlation";
import { formatValue } from "../../lib/industrial-signals/explorer";
import { plantLabel, targetOptions } from "../../lib/predictive/source";
import { fetchDatasets } from "../../lib/quality-analytics/api";
import { fetchProcessJoin, JOIN_SIGNALS, joinSignalId, REAL_DATASET_ID } from "../../lib/quality-analytics/processJoin";

// IQ-F13 "Vista A" (docs/design/process-quality-join.md): the customer's REAL
// pieces joined by time with simulated process signals on the same calendar.
// Illustrative only: no cycle → piece traceability between the two sources.
// IQ-F16: workbench look -- pane-header card, segmented control, KPI tiles,
// neutral notice; neutral scatter, and in the time view the real NOK rate in
// the muted NOK accent above the simulated signal in the dark neutral mark.

const BUCKETS = [15, 30, 60] as const;
const selectClass =
  "mt-1 block w-full rounded-md border border-border bg-surface px-2 py-1.5 text-sm font-medium normal-case tracking-normal text-text-primary focus:outline-none focus:ring-2 focus:ring-brand-accent";

function Header() {
  return (
    <CardHeader
      title="Vista A: piezas reales + sensores simulados"
      action={
        <div className="flex flex-wrap items-center gap-2">
          <OriginBadge origin="REAL" />
          <OriginBadge origin="SIMULATED" />
          <OriginBadge origin="EXPERIMENTAL" />
        </div>
      }
    />
  );
}

export function QualityJoinPanel() {
  const datasets = useAsync(fetchDatasets, []);
  const real = datasets.data?.items.find((d) => d.id === REAL_DATASET_ID) ?? null;

  if (datasets.loading && !datasets.data) return null;
  if (!real) {
    return (
      <Card className="space-y-1">
        <Header />
        <p className="text-sm text-text-secondary">
          Necesita el dataset REAL del cliente, que solo se carga en una instalación local. Une por tiempo las piezas inspeccionadas
          con señales de proceso simuladas en el mismo calendario: es una superposición ilustrativa, no una relación medida.
        </p>
      </Card>
    );
  }
  return <JoinView targets={targetOptions(real)} />;
}

function JoinView({ targets }: { targets: { value: string; label: string }[] }) {
  const [signal, setSignal] = useState(JOIN_SIGNALS[0].key);
  const [target, setTarget] = useState(targets[0]?.value ?? "total");
  const [bucket, setBucket] = useState<number>(30);
  const [lag, setLag] = useState(0);
  const result = useAsync(
    () => fetchProcessJoin({ dataset: REAL_DATASET_ID, signal: joinSignalId(signal), target, bucketMinutes: bucket, lagMinutes: lag }),
    [signal, target, bucket, lag],
  );
  const data = result.data;
  const offset = data?.utc_offset_minutes ?? 0;

  const series = useMemo(() => (data ? data.buckets.map((b) => ({ ...b, nok: b.y * 100 })) : []), [data]);
  // Time charts: a null point between buckets that are not consecutive (a stop or a
  // bucket under the minimum) so the line is cut instead of bridging the gap.
  const timeline = useMemo(() => {
    if (!data) return [];
    const step = data.bucket_minutes * 60;
    const out: { start_ts: number; nok: number | null; x: number | null }[] = [];
    series.forEach((b, i) => {
      if (i > 0 && b.start_ts - series[i - 1].start_ts > step * 1.5) {
        out.push({ start_ts: series[i - 1].start_ts + step, nok: null, x: null });
      }
      out.push({ start_ts: b.start_ts, nok: b.nok, x: b.x });
    });
    return out;
  }, [data, series]);
  const fitSegment = useMemo(() => {
    if (!data || data.slope === null || data.intercept === null || series.length === 0) return null;
    const xs = series.map((p) => p.x);
    const x0 = Math.min(...xs);
    const x1 = Math.max(...xs);
    return [
      { x: x0, y: (data.intercept + data.slope * x0) * 100 },
      { x: x1, y: (data.intercept + data.slope * x1) * 100 },
    ];
  }, [data, series]);

  return (
    <Card className="space-y-3">
      <Header />
      <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto_auto]">
        <label className="wb-label">
          Señal simulada (X)
          <select className={selectClass} value={signal} onChange={(e) => setSignal(e.target.value)} aria-label="Señal simulada">
            {JOIN_SIGNALS.map((s) => (
              <option key={s.key} value={s.key}>
                INY-01 · {s.label}
              </option>
            ))}
          </select>
        </label>
        <label className="wb-label">
          NOK real (Y)
          <select className={selectClass} value={target} onChange={(e) => setTarget(e.target.value)} aria-label="Objetivo NOK">
            {targets.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </label>
        <fieldset>
          <legend className="wb-label">Intervalo</legend>
          <div className="wb-seg mt-1">
            {BUCKETS.map((b) => (
              <button
                key={b}
                type="button"
                aria-pressed={bucket === b}
                onClick={() => {
                  setBucket(b);
                  setLag(0);
                }}
              >
                {b} min
              </button>
            ))}
          </div>
        </fieldset>
        <label className="wb-label">
          Desfase (min)
          <input
            type="number"
            className={`${selectClass} font-mono`}
            value={lag}
            min={-180}
            max={180}
            step={bucket}
            onChange={(e) => setLag(Math.max(-180, Math.min(180, Math.round((Number(e.target.value) || 0) / bucket) * bucket)))}
            aria-label="Desfase en minutos"
          />
        </label>
      </div>
      <p className="flex items-start gap-2 text-sm text-text-secondary">
        <Info size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
        Por intervalo de tiempo: media de la señal simulada en los ciclos frente a la tasa NOK de las piezas reales inspeccionadas en
        el mismo intervalo (hora de planta). Un desfase positivo compara el proceso con la inspección posterior.
      </p>

      {result.error && (
        <p role="alert" className="text-sm text-status-nok">
          {result.error}
        </p>
      )}
      {result.loading && !data && <p className="text-sm text-text-secondary">Calculando…</p>}

      {data && (
        <>
          {/* Provenance caveat (illustrative join, imposed or control relation), not an alarm. */}
          <Notice icon={<FlaskConical size={16} aria-hidden="true" />}>
            <div className="space-y-1">
              {data.notes.map((note) => (
                <p key={note}>{note}</p>
              ))}
            </div>
          </Notice>

          <div className="wb-kpis cols-4">
            <Kpi size="sm" label="Intervalos (n)" value={data.n.toLocaleString("es-MX")} />
            <Kpi size="sm" label="r de Pearson" value={formatCoefficient(data.pearson_r)} />
            <Kpi size="sm" label="R²" value={formatCoefficient(data.r_squared)} />
            <Kpi
              size="sm"
              label={`Pendiente (pts de % NOK por ${data.signal.unit || "unidad"})`}
              value={data.slope === null ? "—" : formatCoefficient(data.slope * 100)}
            />
          </div>
          <p className="text-sm text-text-primary" aria-live="polite">
            {describeCorrelation(data.pearson_r)}{" "}
            {data.best_lag_minutes !== null && data.best_lag_minutes !== data.lag_minutes && (
              <button type="button" onClick={() => setLag(data.best_lag_minutes ?? 0)} className="wb-chip ml-1">
                Usar desfase óptimo ({data.best_lag_minutes} min)
              </button>
            )}
          </p>

          <div className="grid gap-4 xl:grid-cols-2">
            <div>
              <CardHeader title="Dispersión por intervalo" />
              <ResponsiveContainer width="100%" height={300}>
                <ScatterChart margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis
                    type="number"
                    dataKey="x"
                    domain={["auto", "auto"]}
                    tickFormatter={(v: number) => formatValue(v)}
                    tick={axisTick}
                    label={{ value: `${data.signal.name} (${data.signal.unit})`, position: "insideBottom", offset: -12, fontSize: 11, fill: "var(--text-secondary)" }}
                  />
                  <YAxis
                    type="number"
                    dataKey="nok"
                    domain={[0, "auto"]}
                    width={56}
                    tickFormatter={(v: number) => `${formatValue(v)} %`}
                    tick={axisTick}
                  />
                  <Tooltip formatter={(value: number) => formatValue(value)} contentStyle={tooltipStyle} />
                  <Scatter data={series} fill={WB.bar} fillOpacity={0.6} isAnimationActive={false} />
                  {fitSegment && <ReferenceLine segment={fitSegment} stroke={WB.ref} strokeWidth={2} ifOverflow="extendDomain" />}
                </ScatterChart>
              </ResponsiveContainer>
            </div>
            <div>
              <CardHeader title="En el tiempo (hora de planta)" />
              <ResponsiveContainer width="100%" height={140}>
                <LineChart data={timeline} syncId="vista-a" margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="start_ts" type="number" domain={["dataMin", "dataMax"]} hide />
                  <YAxis width={56} tick={axisTick} tickFormatter={(v: number) => `${formatValue(v)} %`} />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    labelFormatter={(ts: number) => plantLabel(ts, offset)}
                    formatter={(v: number) => [`${formatValue(v)} %`, data.target_label]}
                  />
                  <Line dataKey="nok" stroke={WB.nok} strokeWidth={2} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
              <ResponsiveContainer width="100%" height={160}>
                <LineChart data={timeline} syncId="vista-a" margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis
                    dataKey="start_ts"
                    type="number"
                    domain={["dataMin", "dataMax"]}
                    tick={axisTick}
                    tickFormatter={(ts: number) => plantLabel(ts, offset)}
                  />
                  <YAxis width={56} tick={axisTick} tickFormatter={(v: number) => formatValue(v)} domain={["auto", "auto"]} />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    labelFormatter={(ts: number) => plantLabel(ts, offset)}
                    formatter={(v: number) => [`${formatValue(v)} ${data.signal.unit}`, `${data.signal.name} (simulada)`]}
                  />
                  <Line dataKey="x" stroke={WB.mark} strokeWidth={1.5} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
              <p className="text-xs text-text-secondary">
                Arriba: {data.target_label} de las piezas reales. Abajo: {data.signal.name} simulada en el escenario «calendario real».
              </p>
            </div>
          </div>
        </>
      )}
    </Card>
  );
}
