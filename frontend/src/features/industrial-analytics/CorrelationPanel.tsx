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
import { WB, axisTick, gridProps, lineLabel, refLine, tooltipStyle } from "../../lib/demo/chartTheme";
import { useAsync } from "../../lib/catalog/hooks";
import { useDemoSession } from "../../lib/demo/DemoSessionProvider";
import { collectSignals, fetchCorrelation, fetchSignalTree } from "../../lib/industrial-signals/api";
import { describeCorrelation, equation, formatCoefficient } from "../../lib/industrial-signals/correlation";
import { formatValue } from "../../lib/industrial-signals/explorer";
import type { AlignMode } from "../../lib/industrial-signals/types";
import { QualityJoinPanel } from "./QualityJoinPanel";

// IQ-F4: real scatter / OLS / Pearson / lag scan computed by the backend on
// time-aligned simulated pairs. Wording stays at "association" level.
// IQ-F16: workbench look -- chips, segmented control, KPI tiles, neutral notice;
// neutral scatter with the regression line in the text color.

const SID = (key: string) => `L1.INY-01.${key}`;

interface Preset {
  label: string;
  scenario: string;
  x: string;
  y: string;
  mode: AlignMode;
}

const PRESETS: Preset[] = [
  {
    label: "Presión de mantenimiento → longitud",
    scenario: "pressure_setpoint_change",
    x: SID("holding_pressure"),
    y: SID("dim_pins_length"),
    mode: "cycle",
  },
  {
    label: "Temperatura de molde → longitud",
    scenario: "thermal_drift",
    x: SID("mold_temp"),
    y: SID("dim_pins_length"),
    mode: "cycle",
  },
  {
    label: "Humedad ambiente → longitud (control)",
    scenario: "normal",
    x: SID("ambient_humidity"),
    y: SID("dim_pins_length"),
    mode: "cycle",
  },
  {
    label: "Unión por tiempo: desfase de inspección",
    scenario: "normal",
    x: SID("holding_pressure"),
    y: SID("dim_pins_length"),
    mode: "time",
  },
];

const selectClass =
  "mt-1 block w-full rounded-md border border-border bg-surface px-2 py-1.5 text-sm font-medium normal-case tracking-normal text-text-primary";

export function CorrelationPanel() {
  const { scenarioId, setScenarioId } = useDemoSession();
  const [x, setX] = useState(PRESETS[0].x);
  const [y, setY] = useState(PRESETS[0].y);
  const [mode, setMode] = useState<AlignMode>("cycle");
  const [lag, setLag] = useState(0);

  const tree = useAsync(fetchSignalTree, []);
  const options = useMemo(
    () => (tree.data ? collectSignals(tree.data.root).flatMap((leaf) => (leaf.signal ? [leaf.signal] : [])) : []),
    [tree.data],
  );
  const result = useAsync(
    () => fetchCorrelation({ scenarioId, x, y, mode, lag }),
    [scenarioId, x, y, mode, lag],
  );
  const data = result.data;
  const lagUnit = mode === "cycle" ? "ciclos" : "s";

  function applyPreset(preset: Preset) {
    setScenarioId(preset.scenario);
    setX(preset.x);
    setY(preset.y);
    setMode(preset.mode);
    setLag(0);
  }

  const scatter = useMemo(() => (data ? data.points.map(([px, py]) => ({ x: px, y: py })) : []), [data]);
  const fitSegment = useMemo(() => {
    if (!data || data.slope === null || data.intercept === null || scatter.length === 0) return null;
    const xs = scatter.map((p) => p.x);
    const x0 = Math.min(...xs);
    const x1 = Math.max(...xs);
    return [
      { x: x0, y: data.intercept + data.slope * x0 },
      { x: x1, y: data.intercept + data.slope * x1 },
    ];
  }, [data, scatter]);

  return (
    <div className="space-y-4">
      <Card className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((preset) => (
            <button key={preset.label} type="button" onClick={() => applyPreset(preset)} className="wb-chip">
              {preset.label}
            </button>
          ))}
        </div>
        <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto_auto]">
          <label className="wb-label">
            Señal X (predictora)
            <select className={selectClass} value={x} onChange={(e) => setX(e.target.value)} aria-label="Señal X">
              {options.map((s) => (
                <option key={s.signal_id} value={s.signal_id}>
                  {s.machine_code} · {s.name} ({s.unit})
                </option>
              ))}
            </select>
          </label>
          <label className="wb-label">
            Señal Y (respuesta)
            <select className={selectClass} value={y} onChange={(e) => setY(e.target.value)} aria-label="Señal Y">
              {options.map((s) => (
                <option key={s.signal_id} value={s.signal_id}>
                  {s.machine_code} · {s.name} ({s.unit})
                </option>
              ))}
            </select>
          </label>
          <fieldset>
            <legend className="wb-label">Alineación</legend>
            <div className="wb-seg mt-1">
              {(["cycle", "time"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  aria-pressed={mode === m}
                  onClick={() => {
                    setMode(m);
                    setLag(0);
                  }}
                >
                  {m === "cycle" ? "Por ciclo" : "Por tiempo"}
                </button>
              ))}
            </div>
          </fieldset>
          <label className="wb-label">
            Desfase ({lagUnit})
            <input
              type="number"
              className={`${selectClass} font-mono`}
              value={lag}
              step={mode === "cycle" ? 1 : 30}
              onChange={(e) => setLag(Number(e.target.value) || 0)}
              aria-label={`Desfase en ${lagUnit}`}
            />
          </label>
        </div>
        <p className="flex items-start gap-2 text-sm text-text-secondary">
          <Info size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
          {mode === "cycle"
            ? "Por ciclo: un par por disparo. Equivale a tener trazabilidad ciclo → pieza, perfecta en la simulación y que en planta exige integración."
            : "Por tiempo: x(t) frente a y(t + desfase), sin trazabilidad. El retraso de inspección debe estimarse; el barrido de desfase lo busca."}
        </p>
      </Card>

      {result.error && (
        <p role="alert" className="text-sm text-status-nok">
          {result.error}
        </p>
      )}
      {result.loading && !data && <p className="text-sm text-text-secondary">Calculando…</p>}

      {data && (
        <>
          {/* Provenance caveat, not an alarm: a neutral notice either way. */}
          <Notice icon={<FlaskConical size={16} aria-hidden="true" />}>
            {data.causal_imposed
              ? "Simulación: relación causal impuesta. La cota sintética se programó para depender de temperatura de molde, presión de mantenimiento y nido; sirve para demostrar la técnica, no como evidencia de planta."
              : "Asociación entre señales simuladas. Una correlación no implica causalidad."}
          </Notice>

          <div className="wb-kpis">
            <Kpi size="sm" label="Pares (n)" value={data.n.toLocaleString("es-MX")} />
            <Kpi size="sm" label="r de Pearson" value={formatCoefficient(data.pearson_r)} />
            <Kpi size="sm" label="R²" value={formatCoefficient(data.r_squared)} />
            <div className="col-span-2 grid min-w-0">
              <Kpi size="sm" label="Ecuación" value={equation(data.slope, data.intercept)} />
            </div>
            <Kpi size="sm" label={`Desfase (${lagUnit})`} value={formatValue(data.lag)} />
          </div>
          <p className="text-sm text-text-primary" aria-live="polite">
            {describeCorrelation(data.pearson_r)}{" "}
            <span className="text-text-secondary">
              Pendiente: {formatCoefficient(data.slope)} {data.y.unit}/{data.x.unit}.
            </span>
          </p>

          <div className="grid gap-4 xl:grid-cols-2">
            <Card>
              <CardHeader title="Dispersión y recta de regresión" action={<OriginBadge origin="SIMULATED" />} />
              <ResponsiveContainer width="100%" height={300}>
                <ScatterChart margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis
                    type="number"
                    dataKey="x"
                    domain={["auto", "auto"]}
                    tickFormatter={(v: number) => formatValue(v)}
                    tick={axisTick}
                    label={{ value: `${data.x.name} (${data.x.unit})`, position: "insideBottom", offset: -12, fontSize: 11, fill: "var(--text-secondary)" }}
                  />
                  <YAxis
                    type="number"
                    dataKey="y"
                    domain={["auto", "auto"]}
                    width={64}
                    tickFormatter={(v: number) => formatValue(v)}
                    tick={axisTick}
                    label={{ value: data.y.unit, angle: -90, position: "insideLeft", fontSize: 11, fill: "var(--text-secondary)" }}
                  />
                  <Tooltip formatter={(value: number) => formatValue(value)} contentStyle={tooltipStyle} />
                  <Scatter data={scatter} fill={WB.bar} fillOpacity={0.5} isAnimationActive={false} />
                  {fitSegment && <ReferenceLine segment={fitSegment} stroke={WB.ref} strokeWidth={2} ifOverflow="extendDomain" />}
                </ScatterChart>
              </ResponsiveContainer>
            </Card>

            <Card>
              <CardHeader
                title="Barrido de desfase"
                action={
                  data.best_lag !== null && data.best_lag !== data.lag ? (
                    <button type="button" onClick={() => setLag(data.best_lag ?? 0)} className="wb-chip">
                      Usar desfase óptimo ({formatValue(data.best_lag)} {lagUnit})
                    </button>
                  ) : null
                }
              />
              {data.lag_scan.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={260}>
                    <LineChart data={data.lag_scan} margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
                      <CartesianGrid {...gridProps} />
                      <XAxis
                        dataKey="lag"
                        type="number"
                        domain={["dataMin", "dataMax"]}
                        tick={axisTick}
                        label={{ value: `Desfase (${lagUnit})`, position: "insideBottom", offset: -12, fontSize: 11, fill: "var(--text-secondary)" }}
                      />
                      <YAxis domain={[-1, 1]} tick={axisTick} width={40} />
                      <Tooltip
                        contentStyle={tooltipStyle}
                        formatter={(value: number) => formatCoefficient(value)}
                        labelFormatter={(l: number) => `Desfase ${l} ${lagUnit}`}
                      />
                      <ReferenceLine y={0} {...refLine} stroke={WB.text} />
                      {data.best_lag !== null && (
                        <ReferenceLine x={data.best_lag} {...refLine} label={bestLagLabel(data.best_lag, data.lag_scan)} />
                      )}
                      <Line dataKey="pearson_r" stroke={WB.mark} strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
                    </LineChart>
                  </ResponsiveContainer>
                  <p className="text-xs text-text-secondary">
                    Máximo |r| en {formatValue(data.best_lag)} {lagUnit}. En derivas lentas varios desfases dan r parecido: el
                    desfase solo es identificable cuando la señal varía de ciclo a ciclo.
                  </p>
                </>
              ) : (
                <p className="text-sm text-text-secondary">Sin barrido para esta consulta.</p>
              )}
            </Card>
          </div>
        </>
      )}

      <QualityJoinPanel />
    </div>
  );
}

// "MÁX. |R|" label on the best-lag line, set on the side with room for it.
function bestLagLabel(best: number, scan: { lag: number }[]) {
  const lags = scan.map((p) => p.lag);
  const mid = (Math.min(...lags) + Math.max(...lags)) / 2;
  return lineLabel("Máx. |r|", best > mid ? "insideTopRight" : "insideTopLeft");
}
