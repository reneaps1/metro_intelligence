import { useState } from "react";
import { AlertTriangle, FlaskConical } from "lucide-react";
import { Bar, BarChart, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardHeader } from "../../components/ui/Card";
import { Notice } from "../../components/workbench/Notice";
import { useAsync } from "../../lib/catalog/hooks";
import { WB, barValueLabel, lineLabel, refLine } from "../../lib/demo/chartTheme";
import { fetchModelLab } from "../../lib/predictive/api";
import type { ModelLab as ModelLabData, ModelMetrics } from "../../lib/predictive/types";
import { formatPct } from "../../lib/quality-analytics/filters";
import { Callout, LoadState, Metric, PanelHeader, axisTick, fieldControl, n, tooltipStyle } from "./shared";

// IQ-F7: results of a closed historical ML/DL study (PRECOMPUTED). No ROC/PR
// curves and no threshold slider: per-threshold results were not delivered,
// so nothing is drawn that the study did not produce.
// IQ-F16: neutral marks -- ML tabular in the dark mark, deep learning outlined
// in it, the baseline in the plain bar gray; the NOK that escape carry the
// muted NOK accent.

const FAMILY_STYLE = {
  ml_tabular: { fill: WB.mark, stroke: WB.mark },
  deep_learning: { fill: WB.soft, stroke: WB.mark },
  baseline: { fill: WB.bar, stroke: WB.bar },
} as const;
const FAMILY_LABEL = { ml_tabular: "ML tabular", deep_learning: "Deep learning", baseline: "Línea base" } as const;

type MetricKey = "roc_auc" | "pr_auc" | "recall" | "precision";
const METRICS: { key: MetricKey; label: string; hint: string }[] = [
  { key: "roc_auc", label: "ROC-AUC", hint: "0.5 = azar" },
  { key: "pr_auc", label: "PR-AUC", hint: "línea = azar (prevalencia)" },
  { key: "recall", label: "Recall NOK", hint: "NOK detectados / NOK reales" },
  { key: "precision", label: "Precisión NOK", hint: "NOK reales / piezas alertadas" },
];

function MetricChart({ lab, metric }: { lab: ModelLabData; metric: (typeof METRICS)[number] }) {
  const data = lab.models.map((m) => ({ name: m.name, value: m[metric.key] * 100, family: m.family }));
  const reference = metric.key === "pr_auc" ? lab.prevalence * 100 : metric.key === "roc_auc" ? 50 : null;
  return (
    <Card>
      <CardHeader title={metric.label} action={<span className="text-xs text-text-secondary">{metric.hint}</span>} />
      <ResponsiveContainer width="100%" height={170}>
        <BarChart data={data} layout="vertical" margin={{ top: 16, right: 40, bottom: 0, left: 8 }}>
          <XAxis type="number" tick={axisTick} unit=" %" domain={[0, metric.key === "roc_auc" ? 100 : "auto"]} />
          <YAxis type="category" dataKey="name" tick={axisTick} width={180} />
          <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => [`${n(v, 2)} %`, metric.label]} />
          <Bar
            dataKey="value"
            isAnimationActive={false}
            label={{ ...barValueLabel, position: "right", formatter: (v: number) => `${n(v, 1)}` }}
          >
            {data.map((d) => (
              <Cell key={d.name} {...FAMILY_STYLE[d.family]} strokeWidth={1.5} />
            ))}
          </Bar>
          {reference !== null && (
            <ReferenceLine x={reference} {...refLine} ifOverflow="extendDomain" label={{ ...lineLabel("Azar"), position: "top" }} />
          )}
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}

function ConfusionMatrix({ m }: { m: ModelMetrics }) {
  const c = m.confusion;
  // The NOK that escape (FN) are what has to stand out.
  const cells: [string, number, boolean][] = [
    ["NOK detectados (VP)", c.tp, false],
    ["Falsas alarmas (FP)", c.fp, false],
    ["NOK no detectados (FN)", c.fn, true],
    ["OK sin alerta (VN)", c.tn, false],
  ];
  return (
    <div aria-label={`Matriz de confusión ${m.name}`}>
      <Card className="h-full space-y-2">
        <CardHeader title={m.name} action={<span className="text-xs text-text-secondary">{FAMILY_LABEL[m.family]}</span>} />
        <div className="grid grid-cols-2 gap-1.5">
          {cells.map(([label, value, nok]) => (
            <div key={label} className="rounded border border-border px-2.5 py-2">
              <p className="text-xs text-text-secondary">{label}</p>
              <p className={`font-mono text-lg font-semibold ${nok ? "wb-nok" : "text-text-primary"}`}>{n(value)}</p>
            </div>
          ))}
        </div>
        <p className="text-sm text-text-primary">
          <span className="font-mono font-semibold">{m.fp_per_tp === null ? "—" : n(m.fp_per_tp, 1)}</span> falsas alarmas
          por cada NOK detectado · {formatPct(m.alarm_rate, 1)} de las piezas a revisión
        </p>
        {m.confusion_approximate && <p className="text-xs text-text-secondary">Matriz aproximada. {m.note}</p>}
        {!m.consistent && (
          <Notice attention icon={<AlertTriangle size={16} aria-hidden="true" />}>
            Recall/precisión reportados no coinciden con la matriz: revisar la fuente antes de presentar.
          </Notice>
        )}
      </Card>
    </div>
  );
}

function Conclusions({ lab }: { lab: ModelLabData }) {
  const byKey = Object.fromEntries(lab.models.map((m) => [m.key, m]));
  const ml = lab.best_ml ? byKey[lab.best_ml] : null;
  const dl = lab.best_dl ? byKey[lab.best_dl] : null;
  const lowest = Math.min(...lab.models.map((m) => m.fp_per_tp ?? Infinity));
  return (
    <div className="space-y-2">
      {ml && dl && (
        <Callout tone={lab.dl_beats_ml ? "info" : "warning"}>
          <strong>{lab.dl_beats_ml ? "El deep learning superó al ML tabular" : "El deep learning no superó al ML tabular"}</strong>{" "}
          en PR-AUC: {dl.name} {n(dl.pr_auc * 100, 2)} % frente a {ml.name} {n(ml.pr_auc * 100, 2)} % (azar ={" "}
          {n(lab.prevalence * 100, 2)} %).
        </Callout>
      )}
      <Callout tone="nok">
        <strong>Las falsas alarmas impiden el rechazo automático.</strong> Incluso el modelo más selectivo genera{" "}
        {Number.isFinite(lowest) ? n(lowest, 1) : "—"} falsas alarmas por cada NOK detectado: sirve para priorizar
        revisión o muestreo, no para rechazar piezas sin inspección. Cualquier uso requiere validación en planta.
      </Callout>
    </div>
  );
}

export function ModelLab() {
  const lab = useAsync(fetchModelLab, []);
  // IQ-F12: a private file may carry several studies, each on its own test set.
  const [index, setIndex] = useState(0);
  const studies = lab.data ? [lab.data, ...(lab.data.additional_studies ?? [])] : [];
  const data = studies.length ? studies[Math.min(index, studies.length - 1)] : undefined;
  return (
    <section className="space-y-4" aria-label="Laboratorio ML/DL">
      <PanelHeader title="Resultados ML/DL del estudio histórico" origins={["PRECOMPUTED", "HISTORICAL"]}>
        Métricas de un estudio cerrado, no de un modelo en línea. Se muestran tal como se reportaron, con lo que se
        deriva aritméticamente de cada matriz de confusión.
      </PanelHeader>
      <LoadState loading={lab.loading} error={lab.error} onRetry={lab.refetch} />
      {studies.length > 1 && (
        <label className="wb-label block">
          Estudio
          <select
            className={`${fieldControl} max-w-[36rem]`}
            value={Math.min(index, studies.length - 1)}
            onChange={(e) => setIndex(Number(e.target.value))}
            aria-label="Estudio"
          >
            {studies.map((s, i) => (
              <option key={s.title} value={i}>
                {s.title}
              </option>
            ))}
          </select>
        </label>
      )}
      {data && (
        <>
          {data.illustrative && (
            <Notice role="note" icon={<FlaskConical size={16} aria-hidden="true" />}>
              <strong>Ejemplo ilustrativo (cifras ficticias).</strong> Configure el archivo privado del estudio para
              mostrar las cifras reales.
            </Notice>
          )}
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Metric label="Piezas de prueba" value={n(data.test_n)} hint={data.study_date} />
            <Metric
              label="NOK en prueba"
              value={n(data.test_positives)}
              hint={`prevalencia ${formatPct(data.prevalence, 2)}`}
              tone="nok"
            />
            <Metric label="Variables" value={data.variables === null ? "—" : n(data.variables)} hint="variables del modelo" />
            <Metric label="Modelos comparados" value={n(data.models.length)} hint="mismo conjunto de prueba" />
          </div>
          <p className="text-xs text-text-secondary">
            {data.dataset_description} {data.split_description}
          </p>
          <p className="flex flex-wrap gap-4 text-xs text-text-secondary" aria-label="Leyenda de familias">
            {(Object.keys(FAMILY_LABEL) as (keyof typeof FAMILY_LABEL)[])
              .filter((family) => data.models.some((m) => m.family === family))
              .map((family) => (
              <span key={family} className="inline-flex items-center gap-1.5">
                <span
                  className="inline-block h-3 w-3 rounded-sm"
                  style={{ background: FAMILY_STYLE[family].fill, border: `1.5px solid ${FAMILY_STYLE[family].stroke}` }}
                  aria-hidden="true"
                />
                {FAMILY_LABEL[family]}
              </span>
            ))}
          </p>
          <div className="grid gap-3 lg:grid-cols-2">
            {METRICS.map((metric) => (
              <MetricChart key={metric.key} lab={data} metric={metric} />
            ))}
          </div>
          <div className="grid gap-3 lg:grid-cols-3">
            {data.models.map((m) => (
              <ConfusionMatrix key={m.key} m={m} />
            ))}
          </div>
          <Conclusions lab={data} />
          {!data.has_threshold_results && (
            <p className="text-xs text-text-secondary">
              Sin curvas ROC/PR ni umbral interactivo: el estudio entregó métricas agregadas, no resultados por umbral.
              No se dibuja lo que el estudio no produjo.
            </p>
          )}
          {data.notes.length > 0 && (
            <ul className="list-disc pl-5 text-xs text-text-secondary">
              {data.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
