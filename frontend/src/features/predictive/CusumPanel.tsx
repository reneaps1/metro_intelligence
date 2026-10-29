import { useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAsync } from "../../lib/catalog/hooks";
import { WB, gridProps, limitLine, lineLabel, refLine, secondaryLine } from "../../lib/demo/chartTheme";
import { fetchCusum } from "../../lib/predictive/api";
import { SYNTHETIC_SOURCE, plantLabel, type PredictiveSource } from "../../lib/predictive/source";
import { Callout, LoadState, PanelHeader, axisTick, n, tooltipStyle } from "./shared";

// IQ-F7: shadow-mode CUSUM (app/engines/experimental_ml/drift_cusum.py) over an
// hourly series of the synthetic dimensional dataset. Presets point at a known
// mechanism -- and at one series where nothing was injected, to show why the
// output is a hint to investigate, not a verdict.
// IQ-F16: neutral lines with labelled reference and decision limits; only the
// moment of the first alarm carries the muted NOK accent.

interface Preset {
  machine: string;
  series: string;
  label: string;
  /** Known injected mechanism (synthetic only); null on REAL data. */
  truth: string | null;
}

const PRESETS: Preset[] = [
  { machine: "INY-01", series: "PinPositionY", label: "Posición Y · INY-01", truth: "Oleada inyectada el día 1.4 (hora ~34)." },
  { machine: "INY-01", series: "HousingWidth", label: "Ancho de carcasa · INY-01", truth: "Desgaste de herramienta hasta el cambio del día 3.5." },
  { machine: "INY-01", series: "nok_rate", label: "Tasa NOK · INY-01", truth: "Tres oleadas inyectadas (días 1.4, 4.3 y 5.8)." },
  { machine: "INY-02", series: "Coplanarity", label: "Coplanaridad · INY-02", truth: "Sin deriva inyectada: solo un desplazamiento constante." },
];

// IQ-F12: REAL presets come from the dataset (total NOK rate + each station's
// attributed NOK rate); there is no known truth to compare with.
function realPresets(source: PredictiveSource): Preset[] {
  const stations = source.real?.stations ?? [];
  return [
    { machine: "INY-01", series: "nok_rate", label: "Tasa NOK total", truth: null },
    ...stations.map((s) => ({ machine: "INY-01", series: `station:${s.key}`, label: `NOK · ${s.name}`, truth: null })),
  ];
}

// Both charts share the x axis (syncId): same y-axis width and right margin
// (room for the line labels) keep their time scales aligned.
const MARGIN = { top: 8, right: 76, bottom: 0, left: 0 };
const Y_WIDTH = 64;

export function CusumPanel({ source = SYNTHETIC_SOURCE }: { source?: PredictiveSource }) {
  const [preset, setPreset] = useState(0);
  const presets = source.real ? realPresets(source) : PRESETS;
  const p = presets[Math.min(preset, presets.length - 1)];
  const dataset = source.real ? source.datasetId : undefined;
  const study = useAsync(() => fetchCusum(p.machine, p.series, dataset), [p.machine, p.series, dataset]);
  const d = study.data;
  const offset = d?.utc_offset_minutes ?? 0;
  const fmtHour = (ts: number) => plantLabel(ts, offset);
  return (
    <section className="space-y-4" aria-label="CUSUM experimental">
      <PanelHeader
        title="CUSUM experimental sobre una serie"
        origins={source.real ? ["REAL", "EXPERIMENTAL"] : ["SIMULATED", "EXPERIMENTAL"]}
      >
        Suma acumulada de desviaciones respecto de la media de la propia serie (auto-referenciado). Señala un cambio
        sostenido; no dice por qué ocurrió.
      </PanelHeader>
      <div className="flex flex-wrap gap-1.5" role="group" aria-label="Serie">
        {presets.map((item, i) => (
          // Selection, not a call to action: workbench chip with the selected state.
          <button key={item.label} type="button" aria-pressed={i === preset} onClick={() => setPreset(i)} className="wb-chip !min-h-[36px]">
            {item.label}
          </button>
        ))}
      </div>
      <LoadState loading={study.loading && !d} error={study.error} onRetry={study.refetch} />
      {d && (
        <>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={d.points} margin={MARGIN} syncId="cusum">
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="ts" type="number" domain={["dataMin", "dataMax"]} hide />
              <YAxis tick={axisTick} width={Y_WIDTH} domain={["auto", "auto"]} tickFormatter={(v: number) => n(v, 3)} />
              <Tooltip contentStyle={tooltipStyle} labelFormatter={fmtHour} formatter={(v: number) => [n(v, 4), d.series_label]} />
              <Line dataKey="value" stroke={WB.mark} strokeWidth={1.5} dot={false} isAnimationActive={false} />
              {d.target !== null && <ReferenceLine y={d.target} {...refLine} label={lineLabel("Media")} />}
              {d.drift_ts !== null && (
                <ReferenceLine
                  x={d.drift_ts}
                  stroke={WB.nok}
                  strokeWidth={2}
                  label={lineLabel("1ª alarma", "insideTopLeft")}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={d.points} margin={MARGIN} syncId="cusum">
              <CartesianGrid {...gridProps} />
              <XAxis
                dataKey="ts"
                type="number"
                domain={["dataMin", "dataMax"]}
                tick={axisTick}
                tickFormatter={(v: number) => plantLabel(v, offset, false)}
                minTickGap={40}
              />
              <YAxis tick={axisTick} width={Y_WIDTH} tickFormatter={(v: number) => n(v, 3)} />
              <Tooltip contentStyle={tooltipStyle} labelFormatter={fmtHour} formatter={(v: number, name: string) => [n(v, 4), name === "cusum_high" ? "S+ (sube)" : "S− (baja)"]} />
              <Line dataKey="cusum_high" stroke={WB.mark} strokeWidth={1.5} dot={false} isAnimationActive={false} />
              <Line dataKey="cusum_low" {...secondaryLine} dot={false} isAnimationActive={false} />
              {d.h !== null && <ReferenceLine y={d.h} {...limitLine} label={lineLabel("Umbral h")} />}
              {d.drift_ts !== null && <ReferenceLine x={d.drift_ts} stroke={WB.nok} strokeWidth={2} />}
            </LineChart>
          </ResponsiveContainer>
          <p className="text-xs text-text-secondary">
            Arriba: {d.series_label} ({d.unit}); línea punteada = media de referencia. Abajo: S+ (continua) y S−
            (discontinua); línea discontinua gruesa = umbral h = {n(d.h_stdevs, 1)}σ, k = {n(d.k_stdevs, 1)}σ. Línea
            vertical resaltada = primera alarma.
          </p>
          <Callout tone={d.drift_detected ? "warning" : "info"}>
            {d.drift_detected && d.drift_ts !== null ? (
              <>
                <strong>Cambio sostenido {d.drift_direction === "upward" ? "hacia arriba" : "hacia abajo"}</strong> desde{" "}
                {fmtHour(d.drift_ts)}.
              </>
            ) : (
              <strong>Sin cambio sostenido en el período.</strong>
            )}{" "}
            {p.truth === null
              ? "Datos reales sin verdad conocida: contrastar la fecha con la bitácora de planta (paros, cambios de molde, ajustes)."
              : `Verdad conocida del dataset: ${p.truth}`}{" "}
            {p.series === "Coplanarity" && d.drift_detected && "Una alarma aquí es un falso positivo del método: por eso es un indicio a investigar, no una conclusión."}
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
