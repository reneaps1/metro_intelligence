import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardHeader } from "../../components/ui/Card";
import { useAsync } from "../../lib/catalog/hooks";
import { WB, gridProps, limitLine, lineLabel, refLine } from "../../lib/demo/chartTheme";
import { fetchFailureStudy } from "../../lib/predictive/api";
import type { FailureStudy, ThresholdRow } from "../../lib/predictive/types";
import { formatPct } from "../../lib/quality-analytics/filters";
import { Callout, LoadState, Metric, PanelHeader, axisTick, n, tooltipStyle } from "./shared";

// IQ-F7.b: experimental machine-failure prediction on a SIMULATED history.
// The threshold is interactive because the model produced real (simulated)
// scores; every number is computed on the same unseen test period as the
// baselines.
// IQ-F16: neutral lines and bars, the threshold as a labelled limit; the
// failures that had a precursor carry the muted NOK accent.

const DEFAULT_THRESHOLD = 0.5;
const fmt = (v: number | null, digits = 2) => (v === null ? "—" : n(v, digits));

function Timeline({ study, threshold }: { study: FailureStudy; threshold: number }) {
  const t = study.timeline;
  const first = t.points[0]?.hour ?? 0;
  const day = (h: number) => (h - first) / 24;
  const data = t.points.map((p) => ({ ...p, day: day(p.hour) }));
  return (
    <div className="space-y-1">
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey="day" type="number" domain={["dataMin", "dataMax"]} tick={axisTick} tickFormatter={(v: number) => `día ${n(v)}`} />
          <YAxis yAxisId="score" tick={axisTick} width={40} domain={[0, 1]} />
          <YAxis yAxisId="vib" orientation="right" tick={axisTick} width={40} />
          <Tooltip
            contentStyle={tooltipStyle}
            labelFormatter={(v: number) => `Día ${n(v, 1)} del período de prueba`}
            formatter={(v: number, name: string) => [n(v, name === "score" ? 2 : 1), name === "score" ? "Probabilidad de falla (6 h)" : "Vibración mm/s"]}
          />
          <Line yAxisId="vib" dataKey="vibration" stroke={WB.bar} strokeOpacity={0.6} dot={false} isAnimationActive={false} />
          <Line yAxisId="score" dataKey="score" stroke={WB.mark} strokeWidth={1.5} dot={false} isAnimationActive={false} />
          <ReferenceLine yAxisId="score" y={threshold} {...limitLine} label={lineLabel(`Umbral ${n(threshold, 2)}`, "insideTopRight")} />
          {t.maintenance_h.map((h) => (
            <ReferenceLine key={`m${h}`} yAxisId="score" x={day(h)} {...refLine} stroke={WB.bar} />
          ))}
          {t.failures.map((f) => (
            <ReferenceDot
              key={f.hour}
              yAxisId="score"
              x={day(f.hour)}
              y={0.98}
              r={6}
              fill={f.has_precursor ? WB.nok : WB.bar}
              stroke="none"
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      <p className="text-xs text-text-secondary">
        Máquina {t.machine}, período de prueba. Línea oscura: probabilidad de falla en las próximas {study.horizon_h} h.
        Gris claro: vibración. Puntos: fallas (resaltados = con precursor, grises = sin precursor). Punteadas verticales:
        mantenimiento preventivo. Discontinua: umbral.
      </p>
    </div>
  );
}

function PrCurve({ study, row }: { study: FailureStudy; row: ThresholdRow }) {
  const data = study.thresholds
    .filter((r) => r.precision !== null)
    .map((r) => ({ recall: r.recall * 100, precision: (r.precision ?? 0) * 100, threshold: r.threshold }));
  return (
    <Card>
      <CardHeader title="Precisión vs. recall por umbral (por hora)" />
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 8, right: 76, bottom: 0, left: 0 }}>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey="recall" type="number" domain={[0, 100]} tick={axisTick} unit=" %" />
          <YAxis tick={axisTick} width={44} unit=" %" domain={[0, 100]} />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(v: number, name: string) => [`${n(v, 1)} %`, name === "precision" ? "Precisión" : name]}
            labelFormatter={(v: number) => `Recall ${n(v, 1)} %`}
          />
          <Line
            dataKey="precision"
            stroke={WB.mark}
            strokeWidth={1.5}
            dot={{ r: 2, fill: WB.mark, strokeWidth: 0 }}
            isAnimationActive={false}
          />
          <ReferenceLine y={study.split.test_positive_rate * 100} {...refLine} label={lineLabel("Tasa base")} />
          {row.precision !== null && (
            // The chosen threshold: a ring on the curve (a selection, not an alarm).
            <ReferenceDot x={row.recall * 100} y={row.precision * 100} r={6} fill="var(--bg-surface)" stroke={WB.mark} strokeWidth={2} />
          )}
        </LineChart>
      </ResponsiveContainer>
      <p className="text-xs text-text-secondary">
        Calculada con los scores reales del modelo simulado. Línea punteada = tasa base (lo que logra alertar al azar).
        Círculo = umbral elegido.
      </p>
    </Card>
  );
}

function Coefficients({ study }: { study: FailureStudy }) {
  const data = study.features.map((f) => ({ label: f.label, value: f.coefficient }));
  return (
    <Card>
      <CardHeader title="Qué pesa en el modelo (coeficientes estandarizados)" />
      <ResponsiveContainer width="100%" height={Math.max(180, data.length * 22)}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, bottom: 0, left: 8 }}>
          <XAxis type="number" tick={axisTick} />
          <YAxis type="category" dataKey="label" tick={{ ...axisTick, fontSize: 10 }} width={190} />
          <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => [n(v, 2), "Coeficiente"]} />
          <ReferenceLine x={0} stroke={WB.ref} />
          <Bar dataKey="value" isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.label} fill={d.value >= 0 ? WB.mark : WB.bar} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="text-xs text-text-secondary">
        Regresión logística sobre variables estandarizadas: positivo (oscuro, a la derecha) sube el riesgo, negativo (gris)
        lo baja. Variables correlacionadas (p. ej. vibración media y su tendencia) se reparten el efecto, así que un signo
        aislado no es una explicación causal.
      </p>
    </Card>
  );
}

export function FailurePrediction() {
  const study = useAsync(fetchFailureStudy, []);
  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLD);
  const s = study.data;
  const row = s?.thresholds.reduce((best, r) => (Math.abs(r.threshold - threshold) < Math.abs(best.threshold - threshold) ? r : best));
  return (
    <section className="space-y-4" aria-label="Predicción experimental de fallas">
      <PanelHeader title="Predicción experimental de fallas de máquina" origins={["SIMULATED", "EXPERIMENTAL"]}>
        Historial simulado de varias semanas y máquinas: fallas aleatorias por desgaste, algunas con precursores (vibración
        y corriente que suben horas antes) y otras sin aviso. ¿Puede un modelo simple anticiparlas mejor que una regla
        ingenua?
      </PanelHeader>
      <LoadState loading={study.loading} error={study.error} onRetry={study.refetch} />
      {s && row && (
        <>
          <p className="text-xs text-text-secondary">
            {s.split.description} Entrenamiento: {n(s.split.train_rows)} horas, {s.split.train_failures} fallas. Prueba:{" "}
            {n(s.split.test_rows)} horas, {s.split.test_failures} fallas. Objetivo: falla en las próximas {s.horizon_h} h.
          </p>
          <label className="wb-label block">
            Umbral de alerta: <span className="wb-label-inline font-mono text-text-primary">{n(row.threshold, 2)}</span>
            <input
              type="range"
              min={0.05}
              max={0.95}
              step={0.05}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="mt-1 block w-full max-w-md accent-brand-accent"
              aria-label="Umbral de alerta"
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5" aria-label="Métricas al umbral">
            <Metric
              label="Fallas anticipadas"
              value={`${row.episodes_anticipated} de ${row.episodes_total}`}
              hint={`alerta dentro de las ${s.horizon_h} h previas`}
            />
            <Metric label="Anticipación media" value={row.mean_lead_h === null ? "—" : `${n(row.mean_lead_h, 1)} h`} />
            <Metric
              label="Falsas alarmas"
              value={n(row.false_alarms_per_shift, 2)}
              hint={`por turno de 8 h · ${row.alert_events} eventos de alerta`}
            />
            <Metric label="Precisión (por hora)" value={formatPct(row.precision, 1)} hint={`${row.tp} VP · ${row.fp} FP`} />
            <Metric label="Recall (por hora)" value={formatPct(row.recall, 1)} hint={`${row.fn} horas de riesgo sin alerta`} />
          </div>
          <table className="w-full text-left text-sm" aria-label="Comparación con líneas base">
            <thead className="text-xs text-text-secondary">
              <tr className="border-b border-border">
                <th className="p-2 font-medium">Método (mismo período de prueba)</th>
                <th className="p-2 font-medium">PR-AUC</th>
                <th className="p-2 font-medium">Fallas anticipadas</th>
                <th className="p-2 font-medium">Falsas alarmas / turno</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="p-2 font-medium text-text-primary">Regresión logística (umbral {n(row.threshold, 2)})</td>
                <td className="p-2 font-mono">{fmt(s.model_pr_auc, 3)}</td>
                <td className="p-2 font-mono">
                  {row.episodes_anticipated} de {row.episodes_total}
                </td>
                <td className="p-2 font-mono">{fmt(row.false_alarms_per_shift)}</td>
              </tr>
              {s.baselines.map((b) => (
                <tr key={b.key} className="border-b border-border last:border-0 text-text-secondary">
                  <td className="p-2">Línea base: {b.label}</td>
                  <td className="p-2 font-mono">{fmt(b.pr_auc, 3)}</td>
                  <td className="p-2 font-mono">
                    {b.at_half.episodes_anticipated} de {b.at_half.episodes_total}
                  </td>
                  <td className="p-2 font-mono">{fmt(b.at_half.false_alarms_per_shift)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Callout tone="info">
            Con precursor se anticiparon{" "}
            <strong>
              {s.precursor_breakdown.with_precursor_anticipated} de {s.precursor_breakdown.with_precursor_total}
            </strong>{" "}
            fallas; sin precursor,{" "}
            <strong>
              {s.precursor_breakdown.without_precursor_anticipated} de {s.precursor_breakdown.without_precursor_total}
            </strong>{" "}
            (umbral 0.50). El modelo solo es tan bueno como las señales que avisan: una falla sin síntoma previo no se
            puede anticipar.
          </Callout>
          <Timeline study={s} threshold={row.threshold} />
          <div className="grid gap-3 lg:grid-cols-2">
            <PrCurve study={s} row={row} />
            <Coefficients study={s} />
          </div>
          <div className="rounded border border-dashed border-border p-3">
            <p className="wb-label mb-1">Limitaciones y qué haría falta en planta</p>
            <ul className="list-disc pl-5 text-sm text-text-secondary">
              {s.limitations.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </div>
          <p className="text-xs text-text-secondary">
            Motor {s.engine_name} {s.engine_version}. Nunca actúa sobre la máquina: produce indicios para revisión humana.
          </p>
        </>
      )}
    </section>
  );
}
