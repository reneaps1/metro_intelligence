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
import clsx from "clsx";
import { Card, CardHeader } from "../../components/ui/Card";
import { OriginBadge } from "../../components/ui/OriginBadge";
import { useAsync } from "../../lib/catalog/hooks";
import { useDemoSession } from "../../lib/demo/DemoSessionProvider";
import { collectSignals, fetchCorrelation, fetchSignalTree } from "../../lib/industrial-signals/api";
import { describeCorrelation, equation, formatCoefficient } from "../../lib/industrial-signals/correlation";
import { formatValue } from "../../lib/industrial-signals/explorer";
import type { AlignMode } from "../../lib/industrial-signals/types";
import { QualityJoinPanel } from "./QualityJoinPanel";

// IQ-F4: real scatter / OLS / Pearson / lag scan computed by the backend on
// time-aligned simulated pairs. Wording stays at "association" level.

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

const selectClass = "w-full rounded border border-border bg-surface px-2 py-1.5 text-sm text-text-primary";

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
            <button
              key={preset.label}
              type="button"
              onClick={() => applyPreset(preset)}
              className="rounded border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-secondary hover:border-brand-primary hover:text-text-primary"
            >
              {preset.label}
            </button>
          ))}
        </div>
        <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto_auto]">
          <label className="text-xs text-text-secondary">
            Señal X (predictora)
            <select className={selectClass} value={x} onChange={(e) => setX(e.target.value)} aria-label="Señal X">
              {options.map((s) => (
                <option key={s.signal_id} value={s.signal_id}>
                  {s.machine_code} · {s.name} ({s.unit})
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-text-secondary">
            Señal Y (respuesta)
            <select className={selectClass} value={y} onChange={(e) => setY(e.target.value)} aria-label="Señal Y">
              {options.map((s) => (
                <option key={s.signal_id} value={s.signal_id}>
                  {s.machine_code} · {s.name} ({s.unit})
                </option>
              ))}
            </select>
          </label>
          <fieldset className="text-xs text-text-secondary">
            <legend>Alineación</legend>
            <div className="mt-1 flex rounded border border-border">
              {(["cycle", "time"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  aria-pressed={mode === m}
                  onClick={() => {
                    setMode(m);
                    setLag(0);
                  }}
                  className={clsx(
                    "px-3 py-1.5 text-xs font-medium",
                    mode === m ? "bg-brand-primary text-text-on-brand" : "bg-surface text-text-secondary",
                  )}
                >
                  {m === "cycle" ? "Por ciclo" : "Por tiempo"}
                </button>
              ))}
            </div>
          </fieldset>
          <label className="text-xs text-text-secondary">
            Desfase ({lagUnit})
            <input
              type="number"
              className={selectClass}
              value={lag}
              step={mode === "cycle" ? 1 : 30}
              onChange={(e) => setLag(Number(e.target.value) || 0)}
              aria-label={`Desfase en ${lagUnit}`}
            />
          </label>
        </div>
        <p className="flex items-start gap-2 text-xs text-text-secondary">
          <Info size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
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
          <p
            className={clsx(
              "flex items-start gap-2 rounded px-3 py-2 text-sm",
              data.causal_imposed ? "bg-status-warning-bg text-status-warning" : "bg-status-info-bg text-status-info",
            )}
          >
            <FlaskConical size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
            {data.causal_imposed
              ? "Simulación: relación causal impuesta. La cota sintética se programó para depender de temperatura de molde, presión de mantenimiento y nido; sirve para demostrar la técnica, no como evidencia de planta."
              : "Asociación entre señales simuladas. Una correlación no implica causalidad."}
          </p>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
            <Stat label="Pares (n)" value={data.n.toLocaleString("es-MX")} />
            <Stat label="r de Pearson" value={formatCoefficient(data.pearson_r)} />
            <Stat label="R²" value={formatCoefficient(data.r_squared)} />
            <Stat label="Ecuación" value={equation(data.slope, data.intercept)} wide />
            <Stat label={`Desfase (${lagUnit})`} value={formatValue(data.lag)} />
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
                  <CartesianGrid stroke="var(--border-default)" strokeOpacity={0.5} />
                  <XAxis
                    type="number"
                    dataKey="x"
                    domain={["auto", "auto"]}
                    tickFormatter={(v: number) => formatValue(v)}
                    tick={{ fontSize: 11, fill: "var(--text-secondary)" }}
                    label={{ value: `${data.x.name} (${data.x.unit})`, position: "insideBottom", offset: -12, fontSize: 11, fill: "var(--text-secondary)" }}
                  />
                  <YAxis
                    type="number"
                    dataKey="y"
                    domain={["auto", "auto"]}
                    width={64}
                    tickFormatter={(v: number) => formatValue(v)}
                    tick={{ fontSize: 11, fill: "var(--text-secondary)" }}
                    label={{ value: data.y.unit, angle: -90, position: "insideLeft", fontSize: 11, fill: "var(--text-secondary)" }}
                  />
                  <Tooltip
                    formatter={(value: number) => formatValue(value)}
                    contentStyle={{ background: "var(--bg-surface-raised)", border: "1px solid var(--border-default)", fontSize: 12 }}
                  />
                  <Scatter data={scatter} fill="var(--chart-1)" fillOpacity={0.45} isAnimationActive={false} />
                  {fitSegment && (
                    <ReferenceLine segment={fitSegment} stroke="var(--status-nok)" strokeWidth={2} ifOverflow="extendDomain" />
                  )}
                </ScatterChart>
              </ResponsiveContainer>
            </Card>

            <Card>
              <CardHeader
                title="Barrido de desfase"
                action={
                  data.best_lag !== null && data.best_lag !== data.lag ? (
                    <button
                      type="button"
                      onClick={() => setLag(data.best_lag ?? 0)}
                      className="rounded border border-brand-primary px-2 py-1 text-xs font-medium text-brand-primary"
                    >
                      Usar desfase óptimo ({formatValue(data.best_lag)} {lagUnit})
                    </button>
                  ) : null
                }
              />
              {data.lag_scan.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={260}>
                    <LineChart data={data.lag_scan} margin={{ top: 8, right: 16, bottom: 24, left: 8 }}>
                      <CartesianGrid stroke="var(--border-default)" strokeOpacity={0.5} />
                      <XAxis
                        dataKey="lag"
                        type="number"
                        domain={["dataMin", "dataMax"]}
                        tick={{ fontSize: 11, fill: "var(--text-secondary)" }}
                        label={{ value: `Desfase (${lagUnit})`, position: "insideBottom", offset: -12, fontSize: 11, fill: "var(--text-secondary)" }}
                      />
                      <YAxis domain={[-1, 1]} tick={{ fontSize: 11, fill: "var(--text-secondary)" }} width={40} />
                      <Tooltip formatter={(value: number) => formatCoefficient(value)} labelFormatter={(l: number) => `Desfase ${l} ${lagUnit}`} />
                      <ReferenceLine y={0} stroke="var(--text-secondary)" strokeDasharray="3 3" />
                      {data.best_lag !== null && <ReferenceLine x={data.best_lag} stroke="var(--brand-primary)" strokeDasharray="4 2" />}
                      <Line dataKey="pearson_r" stroke="var(--chart-2)" dot={false} isAnimationActive={false} connectNulls />
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

function Stat({ label, value, wide = false }: { label: string; value: string; wide?: boolean }) {
  return (
    <div className={clsx("rounded border border-border bg-surface p-3", wide && "sm:col-span-2")}>
      <p className="text-xs text-text-secondary">{label}</p>
      <p className="whitespace-nowrap font-mono text-base font-semibold text-text-primary">{value}</p>
    </div>
  );
}
