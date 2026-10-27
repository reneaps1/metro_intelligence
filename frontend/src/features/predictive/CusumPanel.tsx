import { useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAsync } from "../../lib/catalog/hooks";
import { fetchCusum } from "../../lib/predictive/api";
import { Callout, LoadState, PanelHeader, axisTick, n, tooltipStyle } from "./shared";

// IQ-F7: shadow-mode CUSUM (app/engines/experimental_ml/drift_cusum.py) over an
// hourly series of the synthetic dimensional dataset. Presets point at a known
// mechanism -- and at one series where nothing was injected, to show why the
// output is a hint to investigate, not a verdict.

const PRESETS = [
  { machine: "INY-01", series: "PinPositionY", label: "Posición Y · INY-01", truth: "Oleada inyectada el día 1.4 (hora ~34)." },
  { machine: "INY-01", series: "HousingWidth", label: "Ancho de carcasa · INY-01", truth: "Desgaste de herramienta hasta el cambio del día 3.5." },
  { machine: "INY-01", series: "nok_rate", label: "Tasa NOK · INY-01", truth: "Tres oleadas inyectadas (días 1.4, 4.3 y 5.8)." },
  { machine: "INY-02", series: "Coplanarity", label: "Coplanaridad · INY-02", truth: "Sin deriva inyectada: solo un desplazamiento constante." },
];

const fmtHour = (ts: number) =>
  new Date(ts * 1000).toLocaleString("es-MX", { timeZone: "UTC", day: "2-digit", month: "short", hour: "2-digit" });

export function CusumPanel() {
  const [preset, setPreset] = useState(0);
  const p = PRESETS[preset];
  const study = useAsync(() => fetchCusum(p.machine, p.series), [p.machine, p.series]);
  const d = study.data;
  return (
    <section className="space-y-4" aria-label="CUSUM experimental">
      <PanelHeader title="CUSUM experimental sobre una serie" origins={["SIMULATED", "EXPERIMENTAL"]}>
        Suma acumulada de desviaciones respecto de la media de la propia serie (auto-referenciado). Señala un cambio
        sostenido; no dice por qué ocurrió.
      </PanelHeader>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Serie">
        {PRESETS.map((item, i) => (
          <button
            key={item.label}
            type="button"
            aria-pressed={i === preset}
            onClick={() => setPreset(i)}
            className={
              i === preset
                ? "rounded border border-brand-primary bg-brand-primary px-3 py-1.5 text-sm text-text-on-brand"
                : "rounded border border-border bg-surface px-3 py-1.5 text-sm text-text-secondary"
            }
          >
            {item.label}
          </button>
        ))}
      </div>
      <LoadState loading={study.loading && !d} error={study.error} />
      {d && (
        <>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={d.points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }} syncId="cusum">
              <CartesianGrid stroke="var(--border-default)" strokeOpacity={0.5} />
              <XAxis dataKey="ts" type="number" domain={["dataMin", "dataMax"]} hide />
              <YAxis tick={axisTick} width={64} domain={["auto", "auto"]} tickFormatter={(v: number) => n(v, 3)} />
              <Tooltip contentStyle={tooltipStyle} labelFormatter={fmtHour} formatter={(v: number) => [n(v, 4), d.series_label]} />
              <Line dataKey="value" stroke="var(--chart-1)" dot={false} isAnimationActive={false} />
              {d.target !== null && <ReferenceLine y={d.target} stroke="var(--text-secondary)" strokeDasharray="4 3" />}
              {d.drift_ts !== null && <ReferenceLine x={d.drift_ts} stroke="var(--status-nok)" />}
            </LineChart>
          </ResponsiveContainer>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={d.points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }} syncId="cusum">
              <CartesianGrid stroke="var(--border-default)" strokeOpacity={0.5} />
              <XAxis
                dataKey="ts"
                type="number"
                domain={["dataMin", "dataMax"]}
                tick={axisTick}
                tickFormatter={(v: number) => new Date(v * 1000).toLocaleDateString("es-MX", { timeZone: "UTC", day: "2-digit", month: "short" })}
                minTickGap={40}
              />
              <YAxis tick={axisTick} width={64} tickFormatter={(v: number) => n(v, 3)} />
              <Tooltip contentStyle={tooltipStyle} labelFormatter={fmtHour} formatter={(v: number, name: string) => [n(v, 4), name === "cusum_high" ? "S+ (sube)" : "S− (baja)"]} />
              <Line dataKey="cusum_high" stroke="var(--status-nok)" dot={false} isAnimationActive={false} />
              <Line dataKey="cusum_low" stroke="var(--chart-2)" dot={false} isAnimationActive={false} />
              {d.h !== null && <ReferenceLine y={d.h} stroke="var(--status-warning)" strokeDasharray="4 3" />}
              {d.drift_ts !== null && <ReferenceLine x={d.drift_ts} stroke="var(--status-nok)" />}
            </LineChart>
          </ResponsiveContainer>
          <p className="text-xs text-text-secondary">
            Arriba: {d.series_label} ({d.unit}); línea punteada = media de referencia. Abajo: S+ (rojo) y S− (azul);
            línea amarilla = umbral h = {n(d.h_stdevs, 1)}σ, k = {n(d.k_stdevs, 1)}σ. Línea roja vertical = primera alarma.
          </p>
          <Callout tone={d.drift_detected ? "warning" : "info"}>
            {d.drift_detected && d.drift_ts !== null ? (
              <>
                <strong>Cambio sostenido {d.drift_direction === "upward" ? "hacia arriba" : "hacia abajo"}</strong> desde{" "}
                {fmtHour(d.drift_ts)}.
              </>
            ) : (
              <strong>Sin cambio sostenido en la semana.</strong>
            )}{" "}
            Verdad conocida del dataset: {p.truth} {p.series === "Coplanarity" && d.drift_detected && "Una alarma aquí es un falso positivo del método: por eso es un indicio a investigar, no una conclusión."}
          </Callout>
          <p className="text-xs text-text-secondary">
            Motor {d.engine_name} {d.engine_version} · {d.points.length} horas · media de referencia{" "}
            {d.target === null ? "—" : n(d.target, 4)} · σ = {d.stdev === null ? "—" : n(d.stdev, 4)}.
          </p>
        </>
      )}
    </section>
  );
}
