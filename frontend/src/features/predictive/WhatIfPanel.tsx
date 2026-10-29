import { useEffect, useState } from "react";
import { FlaskConical } from "lucide-react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardHeader } from "../../components/ui/Card";
import { Notice } from "../../components/workbench/Notice";
import { useAsync } from "../../lib/catalog/hooks";
import { WB, gridProps, lineLabel, refLine } from "../../lib/demo/chartTheme";
import { fetchWhatIf, type WhatIfParams } from "../../lib/predictive/api";
import { formatPct } from "../../lib/quality-analytics/filters";
import { LoadState, Metric, PanelHeader, axisTick, fieldControl, n, tooltipStyle } from "./shared";

// IQ-F7: HYPOTHETICAL what-if over the Vista B synthetic mechanism. It
// evaluates the simulator's own formula, so it says what the simulator would
// do -- never what a real press would do.
// IQ-F16: neutral curves with the current setting as a labelled reference; a
// high hypothetical P(NOK) takes the muted NOK accent.

const DEFAULTS: WhatIfParams = { holdPressure: 620, moldDelta: 0, nest: null, wornInsert: false };

function prob(p: number): string {
  if (p > 0 && p < 0.0001) return `${n(p * 1e6, 1)} ppm`;
  return formatPct(p, 2);
}

function Sweep({
  data,
  current,
  xLabel,
  unit,
}: {
  data: { x: number; nok_probability: number }[];
  current: number;
  xLabel: string;
  unit: string;
}) {
  const rows = data.map((d) => ({ x: d.x, pct: d.nok_probability * 100 }));
  return (
    <Card>
      <CardHeader title={`P(NOK) según ${xLabel}`} />
      <ResponsiveContainer width="100%" height={170}>
        <LineChart data={rows} margin={{ top: 18, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey="x" type="number" domain={["dataMin", "dataMax"]} tick={axisTick} unit={unit} />
          <YAxis tick={axisTick} width={44} unit=" %" domain={[0, 100]} />
          <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => [`${n(v, 2)} %`, "P(NOK)"]} labelFormatter={(v: number) => `${v}${unit}`} />
          <Line dataKey="pct" stroke={WB.mark} strokeWidth={1.5} dot={false} isAnimationActive={false} />
          <ReferenceLine x={current} {...refLine} label={{ ...lineLabel("Ajuste"), position: "top" }} />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}

export function WhatIfPanel() {
  const [draft, setDraft] = useState<WhatIfParams>(DEFAULTS);
  const [applied, setApplied] = useState<WhatIfParams>(DEFAULTS);
  // Sliders move fast: ask the backend once the value settles.
  useEffect(() => {
    const id = setTimeout(() => setApplied(draft), 200);
    return () => clearTimeout(id);
  }, [draft]);
  const result = useAsync(() => fetchWhatIf(applied), [applied.holdPressure, applied.moldDelta, applied.nest, applied.wornInsert]);
  const r = result.data;
  return (
    <section className="space-y-4" aria-label="Simulación what-if">
      <PanelHeader title="What-if sobre el mecanismo sintético" origins={["SIMULATED", "EXPERIMENTAL"]} />
      <Notice role="note" icon={<FlaskConical size={16} aria-hidden="true" />}>
        <strong>HIPOTÉTICO — mecanismo sintético.</strong> Evalúa la fórmula impuesta en el simulador (Vista B). No es una
        predicción de la prensa real ni una recomendación de ajuste.
      </Notice>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="wb-label">
          Presión de mantenimiento:{" "}
          <span className="wb-label-inline font-mono text-text-primary">{draft.holdPressure} bar</span>
          <input
            type="range"
            min={540}
            max={700}
            step={5}
            value={draft.holdPressure}
            onChange={(e) => setDraft({ ...draft, holdPressure: Number(e.target.value) })}
            className="mt-1 block w-full accent-brand-accent"
            aria-label="Presión de mantenimiento"
          />
        </label>
        <label className="wb-label">
          Temperatura de molde (Δ vs. nominal):{" "}
          <span className="wb-label-inline font-mono text-text-primary">
            {draft.moldDelta > 0 ? "+" : ""}
            {draft.moldDelta} °C
          </span>
          <input
            type="range"
            min={-5}
            max={15}
            step={0.5}
            value={draft.moldDelta}
            onChange={(e) => setDraft({ ...draft, moldDelta: Number(e.target.value) })}
            className="mt-1 block w-full accent-brand-accent"
            aria-label="Temperatura de molde"
          />
        </label>
        <label className="wb-label">
          Nido
          <select
            className={fieldControl}
            value={draft.nest ?? ""}
            onChange={(e) => setDraft({ ...draft, nest: e.target.value ? Number(e.target.value) : null })}
          >
            <option value="">Todos (promedio)</option>
            {Array.from({ length: 12 }, (_, i) => i + 1).map((nest) => (
              <option key={nest} value={nest}>
                Nido {nest}
              </option>
            ))}
          </select>
        </label>
        <label className="inline-flex items-center gap-2 text-sm text-text-secondary">
          <input
            type="checkbox"
            checked={draft.wornInsert}
            onChange={(e) => setDraft({ ...draft, wornInsert: e.target.checked })}
            className="accent-brand-accent"
          />
          Inserto desgastado en el nido 7 (+0.04 mm)
        </label>
      </div>
      <LoadState loading={result.loading && !r} error={result.error} onRetry={result.refetch} />
      {r && (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric
              label="Longitud de pines esperada"
              value={`${n(r.mean_mm, 4)} mm`}
              hint={`nominal ${n(r.nominal_mm, 3)} ± ${n(r.tolerance_mm, 3)} · σ pieza ${n(r.piece_sd_mm, 4)}`}
            />
            <Metric
              label="P(NOK) hipotética"
              value={prob(r.nok_probability)}
              tone={r.nok_probability > 0.01 ? "nok" : undefined}
            />
            <Metric label="Con ajustes nominales" value={prob(r.reference_nok_probability)} hint="620 bar, ΔT = 0 °C, sin desgaste" />
          </div>
          <table className="w-full text-left text-sm" aria-label="Contribuciones al desplazamiento">
            <tbody>
              {r.contributions.map((c) => (
                <tr key={c.label} className="border-b border-border last:border-0">
                  <td className="p-2 text-text-secondary">{c.label}</td>
                  <td className="p-2 text-right font-mono text-text-primary">
                    {c.mm >= 0 ? "+" : ""}
                    {n(c.mm, 4)} mm
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="grid gap-3 lg:grid-cols-2">
            <Sweep data={r.hold_sweep} current={r.hold_pressure_bar} xLabel="presión de mantenimiento" unit=" bar" />
            <Sweep data={r.mold_sweep} current={r.mold_delta_c} xLabel="temperatura de molde (Δ)" unit=" °C" />
          </div>
          <p className="text-xs text-text-secondary">{r.mechanism}</p>
          <ul className="list-disc pl-5 text-xs text-text-secondary">
            {r.not_modelled.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
