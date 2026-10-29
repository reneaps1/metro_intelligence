import { useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardHeader } from "../../components/ui/Card";
import { useAsync } from "../../lib/catalog/hooks";
import { WB, gridProps, secondaryLine } from "../../lib/demo/chartTheme";
import { fetchPieceRisk } from "../../lib/predictive/api";
import { plantLabel, targetOptions, type PredictiveSource } from "../../lib/predictive/source";
import type { ScoreEval } from "../../lib/predictive/types";
import { formatPct } from "../../lib/quality-analytics/filters";
import { Callout, LoadState, Metric, PanelHeader, axisTick, fieldControl, legendText, n, tooltipStyle } from "./shared";

// IQ-F12: per-piece NOK risk before inspection on the REAL dataset, trained on
// the earlier days and tested on the last one, always next to two transparent
// baselines on the same test pieces -- if the model does not beat them, the
// panel says so.
// IQ-F16: the model in the dark mark, the baseline dashed, the actual NOK rate
// in the muted NOK accent.

const TEN = 0.1;
const top10 = (e: ScoreEval) => e.top.find((t) => t.share === TEN) ?? e.top[e.top.length - 1];

export function PieceRisk({ source }: { source: PredictiveSource }) {
  const real = source.real;
  const [target, setTarget] = useState("total");
  const study = useAsync(() => fetchPieceRisk(source.datasetId, target), [source.datasetId, target]);
  const d = study.data;
  if (!real) return <p className="text-sm text-text-secondary">Disponible solo con los datos reales del cliente.</p>;
  const offset = d?.utc_offset_minutes ?? 0;
  const rows = d ? [d.model, ...d.baselines] : [];
  const recallCurve = d
    ? d.model.top.map((t, i) => ({
        share: `${Math.round(t.share * 100)} %`,
        model: t.recall * 100,
        cavity: (d.baselines[0]?.top[i]?.recall ?? 0) * 100,
      }))
    : [];
  const hours = (d?.hours ?? []).map((h) => ({ ...h, label: plantLabel(h.ts, offset), risk: h.mean_risk * 100, actual: h.nok_rate * 100 }));

  return (
    <section className="space-y-4" aria-label="Riesgo por pieza">
      <PanelHeader title="Riesgo por pieza antes de inspeccionar" origins={["REAL", "EXPERIMENTAL"]}>
        ¿Qué piezas conviene revisar primero? Solo usa lo que pasó con piezas anteriores (su cavidad, su nido y la línea).
      </PanelHeader>
      <label className="wb-label block">
        NOK que se predice
        <select
          className={fieldControl}
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          aria-label="NOK que se predice"
        >
          {targetOptions(real).map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      <LoadState loading={study.loading && !d} error={study.error} onRetry={study.refetch} />
      {d && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Resultado del modelo">
            <Metric label="Día de prueba" value={d.test_day} hint={`${n(d.test_pieces)} piezas · entrenado con ${n(d.train_pieces)}`} />
            <Metric
              label="NOK en prueba"
              value={formatPct(d.prevalence, 2)}
              hint={`${n(d.test_nok)} piezas: tasa de revisar al azar`}
              tone="nok"
            />
            <Metric
              label="Revisando el 10 % de mayor riesgo"
              value={formatPct(top10(d.model).recall, 0)}
              hint={`de los NOK · precisión ${formatPct(top10(d.model).precision, 1)} (${n(top10(d.model).lift, 1)}× el azar)`}
            />
            <Metric label="ROC-AUC / PR-AUC" value={`${n(d.model.roc_auc, 3)} / ${n(d.model.pr_auc, 3)}`} hint="en el día de prueba" />
          </div>
          <Callout tone={d.beats_baselines ? "info" : "warning"}>
            {d.beats_baselines ? (
              <>
                <strong>El modelo supera a las líneas base</strong> en PR-AUC, aunque por poco: la señal principal sigue siendo la
                tasa reciente de la cavidad.
              </>
            ) : (
              <>
                <strong>El modelo no supera a una regla simple.</strong> La tasa reciente de la cavidad ya ordena casi igual de bien:
                con estos datos la información útil está en la historia de la cavidad. Para anticipar mejor hacen falta señales de
                proceso vinculadas a cada pieza.
              </>
            )}
          </Callout>
          <table className="w-full text-left text-sm" aria-label="Modelo frente a líneas base">
            <thead className="text-xs text-text-secondary">
              <tr className="border-b border-border">
                <th className="p-2 font-medium">Método</th>
                <th className="p-2 font-medium">ROC-AUC</th>
                <th className="p-2 font-medium">PR-AUC</th>
                <th className="p-2 font-medium">Top 10 %: NOK atrapados</th>
                <th className="p-2 font-medium">Precisión</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.key} className="border-b border-border last:border-0">
                  <td className="p-2">{r.name}</td>
                  <td className="p-2 font-mono">{n(r.roc_auc, 3)}</td>
                  <td className="p-2 font-mono">{n(r.pr_auc, 3)}</td>
                  <td className="p-2 font-mono">{formatPct(top10(r).recall, 0)}</td>
                  <td className="p-2 font-mono">{formatPct(top10(r).precision, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {d.alarm_rule && (
            <p className="text-xs text-text-secondary">
              La regla de alarma en su propio punto de operación revisa el {formatPct(d.alarm_rule.share, 1)} de las piezas y
              atrapa el {formatPct(d.alarm_rule.recall, 0)} de los NOK (precisión {formatPct(d.alarm_rule.precision, 1)}).
            </p>
          )}
          <div className="grid gap-3 xl:grid-cols-2">
            <Card>
              <CardHeader title="NOK atrapados según el % de piezas revisadas" />
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={recallCurve} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="share" tick={axisTick} />
                  <YAxis tick={axisTick} width={44} unit=" %" domain={[0, 100]} />
                  <Tooltip contentStyle={tooltipStyle} formatter={(v: number, name: string) => [`${n(v, 1)} %`, name === "model" ? "Modelo" : "Tasa de la cavidad"]} />
                  <Legend formatter={(v: string) => legendText(v === "model" ? "Modelo" : "Línea base: tasa de la cavidad")} />
                  <Line
                    dataKey="model"
                    stroke={WB.mark}
                    strokeWidth={2}
                    dot={{ r: 2.5, fill: WB.mark, strokeWidth: 0 }}
                    isAnimationActive={false}
                  />
                  <Line
                    dataKey="cavity"
                    {...secondaryLine}
                    dot={{ r: 2, fill: secondaryLine.stroke, strokeWidth: 0 }}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>
            <Card>
              <CardHeader title="Riesgo medio estimado vs. NOK real, por hora (día de prueba)" />
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={hours} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="label" tick={axisTick} minTickGap={30} />
                  <YAxis tick={axisTick} width={44} unit=" %" />
                  <Tooltip contentStyle={tooltipStyle} formatter={(v: number, name: string) => [`${n(v, 1)} %`, name === "risk" ? "Riesgo medio" : "NOK real"]} />
                  <Legend formatter={(v: string) => legendText(v === "risk" ? "Riesgo medio estimado" : "NOK real")} />
                  <Line dataKey="risk" stroke={WB.mark} strokeWidth={1.5} dot={false} isAnimationActive={false} />
                  <Line dataKey="actual" stroke={WB.nok} strokeWidth={1.5} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
              <p className="text-xs text-text-secondary">
                El riesgo absoluto no está calibrado (el entrenamiento submuestrea piezas OK); importa el orden, no el nivel.
              </p>
            </Card>
          </div>
          <div className="text-xs text-text-secondary">
            <p className="wb-label mb-1">Peso de cada variable (coeficientes estandarizados)</p>
            <ul className="list-disc pl-5">
              {d.coefficients.map((c) => (
                <li key={c.key}>
                  {c.name}: <span className="font-mono">{n(c.value, 2)}</span>
                </li>
              ))}
            </ul>
          </div>
          <ul className="list-disc pl-5 text-xs text-text-secondary">
            {d.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
          <p className="text-xs text-text-secondary">
            Motor {d.engine_name} {d.engine_version} · {d.target_label}
            {d.excluded_pieces ? ` · ${n(d.excluded_pieces)} piezas sin cavidad o nido excluidas` : ""}.
          </p>
        </>
      )}
    </section>
  );
}
