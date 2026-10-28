import { useState } from "react";
import {
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  ReferenceArea,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { StatusChip } from "../../components/ui/StatusChip";
import { useAsync } from "../../lib/catalog/hooks";
import { fetchNokWaves, type WaveParams } from "../../lib/predictive/api";
import type { EpisodeStatus, WaveStudy } from "../../lib/predictive/types";
import { formatPct } from "../../lib/quality-analytics/filters";
import { SYNTHETIC_SOURCE, plantLabel, targetOptions, type PredictiveSource } from "../../lib/predictive/source";
import { Callout, LoadState, Metric, PanelHeader, axisTick, n, tooltipStyle } from "./shared";

// IQ-F7: NOK waves. A persistence rule (past NOK only) evaluated per
// independent episode against the waves injected in the synthetic dataset:
// detecting a started streak is not predicting its start.
// IQ-F12: on the REAL dataset one piece = one group and episodes are labelled
// with hindsight (no injected truth); times are plant local time.

const STATUS: Record<EpisodeStatus, { label: string; chip: "ok" | "warning" | "nok" }> = {
  anticipated: { label: "Anticipada", chip: "ok" },
  detected: { label: "Detectada ya iniciada", chip: "warning" },
  missed: { label: "No detectada", chip: "nok" },
};

const MAX_EPISODE_ROWS = 20;

function WaveTimeline({ study }: { study: WaveStudy }) {
  const offset = study.utc_offset_minutes ?? 0;
  const fmtTime = (ts: number) => plantLabel(ts, offset);
  const max = Math.max(1, ...study.hours.map((h) => h.nok_pieces));
  const data = study.hours.map((h) => ({ ...h, label: fmtTime(h.ts) }));
  const alerts = study.alert_events.map((a) => ({ ts: a.start, y: max * 1.08, false_alarm: a.false_alarm }));
  return (
    <ResponsiveContainer width="100%" height={260}>
      <ComposedChart data={data} margin={{ top: 12, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--border-default)" strokeOpacity={0.5} vertical={false} />
        <XAxis
          dataKey="ts"
          type="number"
          domain={["dataMin", "dataMax"]}
          tick={axisTick}
          tickFormatter={(v: number) => plantLabel(v, offset, false)}
          minTickGap={40}
        />
        <YAxis tick={axisTick} width={40} allowDecimals={false} domain={[0, Math.ceil(max * 1.15)]} />
        <Tooltip
          contentStyle={tooltipStyle}
          labelFormatter={(v: number) => fmtTime(v)}
          formatter={(value: number, name: string) => (name === "nok_pieces" ? [`${value} piezas`, "NOK en la hora"] : [null, null])}
        />
        {study.episodes.map((e) => (
          <ReferenceArea key={e.start} x1={e.start} x2={e.end} fill="var(--status-nok)" fillOpacity={0.12} ifOverflow="visible" />
        ))}
        <Bar dataKey="nok_pieces" isAnimationActive={false} barSize={3}>
          {data.map((d) => (
            <Cell key={d.ts} fill={d.in_wave ? "var(--status-nok)" : "var(--chart-1)"} />
          ))}
        </Bar>
        <Scatter data={alerts} dataKey="y" isAnimationActive={false} shape="triangle" legendType="none">
          {alerts.map((a) => (
            <Cell key={a.ts} fill={a.false_alarm ? "var(--status-warning)" : "var(--brand-primary)"} />
          ))}
        </Scatter>
      </ComposedChart>
    </ResponsiveContainer>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="text-xs font-semibold text-text-secondary">
      {label}
      <input
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(e) => {
          const v = Number(e.target.value);
          if (Number.isInteger(v) && v >= min && v <= max) onChange(v);
        }}
        className="ml-2 w-16 rounded border border-border bg-surface px-2 py-1 font-mono text-sm text-text-primary"
      />
    </label>
  );
}

export function NokWaves({ source = SYNTHETIC_SOURCE }: { source?: PredictiveSource }) {
  const real = source.real;
  const [p, setP] = useState<WaveParams>(
    real
      ? { machine: "INY-01", window: 100, threshold: 10, horizon: 100, dataset: source.datasetId, target: "total" }
      : { machine: "INY-01", window: 5, threshold: 4, horizon: 15 },
  );
  const study = useAsync(() => fetchNokWaves(p), [p.machine, p.window, p.threshold, p.horizon, p.dataset, p.target]);
  const s = study.data?.summary;
  const unit = real ? "piezas" : "grupos";
  const hours = study.data?.hours ?? [];
  const days = hours.length > 1 ? (hours[hours.length - 1].ts - hours[0].ts) / 86_400 + 1 / 24 : 0;
  const offset = study.data?.utc_offset_minutes ?? 0;
  const episodes = study.data?.episodes ?? [];
  return (
    <section className="space-y-4" aria-label="Oleadas NOK">
      <PanelHeader
        title="Oleadas NOK: detección por persistencia"
        origins={real ? ["REAL", "EXPERIMENTAL"] : ["SIMULATED", "EXPERIMENTAL"]}
      >
        {real
          ? "Serie real pieza por pieza, toda la línea. Sin verdad conocida: los episodios se etiquetan a posteriori. La regla solo mira NOK ya medidos."
          : "Oleadas inyectadas en el dataset dimensional sintético (verdad conocida). La regla solo mira NOK ya medidos."}
      </PanelHeader>
      <div className="flex flex-wrap items-center gap-4">
        {real ? (
          <label className="text-xs font-semibold text-text-secondary">
            NOK que cuenta
            <select
              className="ml-2 rounded border border-border bg-surface px-2 py-1 text-sm text-text-primary"
              value={p.target}
              onChange={(e) => setP({ ...p, target: e.target.value })}
              aria-label="NOK que cuenta"
            >
              {targetOptions(real).map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <label className="text-xs font-semibold text-text-secondary">
            Máquina
            <select
              className="ml-2 rounded border border-border bg-surface px-2 py-1 text-sm text-text-primary"
              value={p.machine}
              onChange={(e) => setP({ ...p, machine: e.target.value })}
            >
              <option value="INY-01">INY-01 (3 oleadas)</option>
              <option value="INY-02">INY-02 (1 oleada)</option>
            </select>
          </label>
        )}
        <NumberField label={`Ventana (${unit})`} value={p.window} min={1} max={real ? 1000 : 50} onChange={(window) => setP({ ...p, window })} />
        <NumberField label="Umbral (piezas NOK)" value={p.threshold} min={1} max={real ? 1000 : 100} onChange={(threshold) => setP({ ...p, threshold })} />
        <NumberField label={`Anticipación (${unit})`} value={p.horizon} min={0} max={real ? 1000 : 60} onChange={(horizon) => setP({ ...p, horizon })} />
      </div>
      <LoadState loading={study.loading && !study.data} error={study.error} onRetry={study.refetch} />
      {study.data && s && (
        <>
          <p className="text-sm text-text-secondary">{study.data.rule}</p>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5" aria-label="Resultado por episodio">
            <Metric
              label={real ? "Episodios" : "Oleadas"}
              value={n(s.episodes)}
              hint={`${study.data.machine}, ${n(days, 1)} días`}
            />
            <Metric label="Anticipadas" value={`${s.anticipated} de ${s.episodes}`} tone={s.anticipated ? "ok" : "nok"} hint="alerta antes del inicio" />
            <Metric
              label="Detectadas ya iniciadas"
              value={`${s.detected} de ${s.episodes}`}
              tone="warning"
              hint={s.mean_delay_min === null ? undefined : `retraso medio ${n(s.mean_delay_min)} min`}
            />
            <Metric
              label="Oleada restante tras la alerta"
              value={formatPct(s.mean_remaining_share, 0)}
              hint="lo que aún se podría contener"
            />
            <Metric
              label="Falsas alarmas"
              value={n(s.false_alarm_events)}
              tone={s.false_alarm_events ? "warning" : undefined}
              hint={`${n(s.false_alarms_per_day, 1)} por día · ${s.alert_events} eventos de alerta`}
            />
          </div>
          <WaveTimeline study={study.data} />
          <p className="text-xs text-text-secondary">
            Barras: piezas NOK por hora (rojo = dentro de una oleada). Franja:{" "}
            {real ? "episodio etiquetado a posteriori" : "oleada inyectada"}. Triángulos: inicio de cada evento de alerta
            (amarillo = falsa alarma).{real ? " Horas en hora local de planta." : ""}
          </p>
          <table className="w-full text-left text-sm" aria-label="Episodios">
            <thead className="text-xs text-text-secondary">
              <tr className="border-b border-border">
                <th className="p-2 font-medium">Inicio de la oleada</th>
                <th className="p-2 font-medium">Duración</th>
                <th className="p-2 font-medium">Resultado</th>
                <th className="p-2 font-medium">Primera alerta</th>
                <th className="p-2 font-medium">Restante al alertar</th>
              </tr>
            </thead>
            <tbody>
              {episodes.slice(0, MAX_EPISODE_ROWS).map((e) => (
                <tr key={e.start} className="border-b border-border last:border-0">
                  <td className="p-2 font-mono">{plantLabel(e.start, offset)}</td>
                  <td className="p-2 font-mono">
                    {n(e.groups)} {unit} (~{n((e.end - e.start) / 3600, 1)} h)
                  </td>
                  <td className="p-2">
                    <StatusChip status={STATUS[e.status].chip} label={STATUS[e.status].label} />
                  </td>
                  <td className="p-2 font-mono">
                    {e.delay_min === null
                      ? "—"
                      : e.delay_min < 0
                        ? `${n(-e.delay_min)} min antes`
                        : `${n(e.delay_min)} min después`}
                  </td>
                  <td className="p-2 font-mono">{formatPct(e.remaining_share, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {episodes.length > MAX_EPISODE_ROWS && (
            <p className="text-xs text-text-secondary">
              Se muestran {MAX_EPISODE_ROWS} de {n(episodes.length)} episodios (los primeros en el tiempo).
            </p>
          )}
          <Callout tone="warning">
            <strong>Detectar una racha iniciada no es predecir su inicio.</strong> La regla anticipó {s.anticipated} de{" "}
            {s.episodes} oleadas: sin señales previas (proceso, máquina) no hay información para adelantarse. Lo que sí
            aporta es contener la racha a tiempo{s.mean_remaining_share !== null && `: alerta con ~${formatPct(s.mean_remaining_share, 0)} de la oleada aún por delante`}.
          </Callout>
          <p className="text-xs text-text-secondary">{study.data.episode_definition}</p>
        </>
      )}
    </section>
  );
}
