import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAsync } from "../../lib/catalog/hooks";
import { fetchGroupAlarms, type GroupAlarmParams } from "../../lib/predictive/api";
import { plantLabel, targetOptions, type PredictiveSource } from "../../lib/predictive/source";
import { formatPct } from "../../lib/quality-analytics/filters";
import { Callout, LoadState, Metric, PanelHeader, axisTick, n, tooltipStyle } from "./shared";

// IQ-F12: retrospective evaluation of a per-cavity (or per-nest) alarm over the
// REAL dataset: when each group would have alarmed, how much NOK came after
// that alarm (what a timely reaction could protect, as an upper bound) and the
// review burden it creates. Shadow mode: nothing here acts on production.

const TOP_GROUPS = 12;

function NumberInput({ label, value, min, max, onChange }: { label: string; value: number; min: number; max: number; onChange: (v: number) => void }) {
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

export function CavityAlarms({ source }: { source: PredictiveSource }) {
  const real = source.real;
  const [p, setP] = useState<GroupAlarmParams>({
    dataset: source.datasetId,
    grouping: "mold_cavity",
    target: "total",
    k: 6,
    n: 30,
    scope: "after_longest_gap",
  });
  const study = useAsync(() => fetchGroupAlarms(p), [p.dataset, p.grouping, p.target, p.k, p.n, p.scope]);
  const d = study.data;
  if (!real) return <p className="text-sm text-text-secondary">Disponible solo con los datos reales del cliente.</p>;
  const offset = d?.utc_offset_minutes ?? 0;
  const prefix = p.grouping === "mold_cavity" ? "C" : "N";
  const groupWord = p.grouping === "mold_cavity" ? "cavidad" : "nido";
  const chart = (d?.groups ?? []).slice(0, TOP_GROUPS).map((g) => ({
    label: `${prefix}${g.group}`,
    before: g.nok - g.nok_after_first_alarm,
    after: g.nok_after_first_alarm,
  }));
  const minutesToFirst =
    d?.first_alarm_ts != null && d.scope_start != null ? (d.first_alarm_ts - d.scope_start) / 60 : null;

  return (
    <section className="space-y-4" aria-label="Alarma por cavidad">
      <PanelHeader title="Alarma por cavidad: ¿habría avisado a tiempo?" origins={["REAL", "EXPERIMENTAL"]}>
        Evaluación retrospectiva sobre el período real: la regla solo usa piezas ya inspeccionadas de cada {groupWord}.
      </PanelHeader>
      <div className="flex flex-wrap items-center gap-4">
        <label className="text-xs font-semibold text-text-secondary">
          Agrupar por
          <select
            className="ml-2 rounded border border-border bg-surface px-2 py-1 text-sm text-text-primary"
            value={p.grouping}
            onChange={(e) => setP({ ...p, grouping: e.target.value as GroupAlarmParams["grouping"] })}
            aria-label="Agrupar por"
          >
            <option value="mold_cavity">Cavidad de molde</option>
            <option value="nest">Nido</option>
          </select>
        </label>
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
        <NumberInput label="Alarma con" value={p.k} min={1} max={200} onChange={(k) => setP({ ...p, k: Math.min(k, p.n) })} />
        <NumberInput label="NOK en las últimas (piezas)" value={p.n} min={1} max={500} onChange={(nn) => setP({ ...p, n: nn, k: Math.min(p.k, nn) })} />
        <label className="text-xs font-semibold text-text-secondary">
          Período
          <select
            className="ml-2 rounded border border-border bg-surface px-2 py-1 text-sm text-text-primary"
            value={p.scope}
            onChange={(e) => setP({ ...p, scope: e.target.value as GroupAlarmParams["scope"] })}
            aria-label="Período evaluado"
          >
            <option value="after_longest_gap">Desde el arranque tras el paro más largo</option>
            <option value="all">Todo el período</option>
          </select>
        </label>
      </div>
      <LoadState loading={study.loading && !d} error={study.error} onRetry={study.refetch} />
      {d && (
        <>
          <p className="text-sm text-text-secondary">{d.rule}</p>
          {d.scope === "after_longest_gap" && d.longest_gap && (
            <p className="text-xs text-text-secondary">
              Paro más largo: sin piezas de {plantLabel(d.longest_gap[0], offset)} a {plantLabel(d.longest_gap[1], offset)} (hora
              local de planta). Se evalúa desde el arranque.
            </p>
          )}
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Resultado de la alarma">
            <Metric
              label="NOK después de la alarma de su grupo"
              value={formatPct(d.share_after_first_alarm, 1)}
              hint={`${n(d.nok_after_first_alarm)} de ${n(d.nok)} piezas NOK`}
              tone="warning"
            />
            <Metric
              label="Primera alarma"
              value={d.first_alarm_ts === null ? "—" : plantLabel(d.first_alarm_ts, offset)}
              hint={minutesToFirst === null ? undefined : `${n(minutesToFirst)} min después del arranque`}
            />
            <Metric label={`Grupos en alarma (${groupWord})`} value={`${n(d.groups_alarmed)} de ${n(d.groups.length)}`} />
            <Metric
              label="Piezas OK revisadas en alarma"
              value={n(d.ok_in_alarm)}
              hint="carga de revisión que generaría la regla"
            />
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chart} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="var(--border-default)" strokeOpacity={0.5} vertical={false} />
              <XAxis dataKey="label" tick={axisTick} interval={0} />
              <YAxis tick={axisTick} width={48} allowDecimals={false} />
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(v: number, name: string) => [`${n(v)} piezas`, name === "after" ? "NOK después de la alarma" : "NOK antes de la alarma"]}
              />
              <Legend formatter={(v: string) => (v === "after" ? "NOK después de la alarma" : "NOK antes de la alarma")} />
              <Bar dataKey="before" stackId="nok" fill="var(--chart-1)" isAnimationActive={false} />
              <Bar dataKey="after" stackId="nok" fill="var(--status-nok)" isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
          <table className="w-full text-left text-sm" aria-label="Alarma por grupo">
            <thead className="text-xs text-text-secondary">
              <tr className="border-b border-border">
                <th className="p-2 font-medium">{p.grouping === "mold_cavity" ? "Cavidad" : "Nido"}</th>
                <th className="p-2 font-medium">Primera alarma</th>
                <th className="p-2 font-medium">NOK</th>
                <th className="p-2 font-medium">Después de la alarma</th>
                <th className="p-2 font-medium">OK en alarma</th>
              </tr>
            </thead>
            <tbody>
              {d.groups.slice(0, TOP_GROUPS).map((g) => (
                <tr key={g.group} className="border-b border-border last:border-0">
                  <td className="p-2 font-mono">
                    {prefix}
                    {g.group}
                  </td>
                  <td className="p-2 font-mono">{g.first_alarm_ts === null ? "sin alarma" : plantLabel(g.first_alarm_ts, offset)}</td>
                  <td className="p-2 font-mono">{n(g.nok)}</td>
                  <td className="p-2 font-mono">
                    {n(g.nok_after_first_alarm)} ({formatPct(g.nok ? g.nok_after_first_alarm / g.nok : null, 0)})
                  </td>
                  <td className="p-2 font-mono">{n(g.ok_in_alarm)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Callout tone="info">
            <strong>Una alarma no evita scrap por sí sola.</strong> El valor está en la reacción: ajustar o bloquear la{" "}
            {groupWord} cuando suena. Este análisis dice cuánto rechazo llegó después del aviso, no cuánto se habría evitado.
          </Callout>
          <ul className="list-disc pl-5 text-xs text-text-secondary">
            {d.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
          <p className="text-xs text-text-secondary">
            Motor {d.engine_name} {d.engine_version} · {d.target_label}.
          </p>
        </>
      )}
    </section>
  );
}
