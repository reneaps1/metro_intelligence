import { useEffect, useMemo, useReducer, useState, type DragEvent } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Info,
  Layers,
  Pause,
  Play,
  RotateCcw,
  Rows3,
  Sparkles,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import clsx from "clsx";
import { Card, CardHeader } from "../../components/ui/Card";
import { Notice } from "../../components/workbench/Notice";
import { useAsync } from "../../lib/catalog/hooks";
import { collectSignals, fetchProcessEvents, fetchSignalTree } from "../../lib/industrial-signals/api";
import {
  INITIAL_EXPLORER_STATE,
  MAX_TRACES,
  clampWindow,
  explorerReducer,
  formatDuration,
  formatRelative,
  groupTracksByUnit,
  panWindow,
  zoomWindow,
  type TimeWindow,
} from "../../lib/industrial-signals/explorer";
import type { ProcessEventSeverity, Scenario, SignalInfo } from "../../lib/industrial-signals/types";
import { useSeries } from "../../lib/industrial-signals/useSeries";
import { LpSymbol } from "../line-panel/parts";
import { SIGNAL_DRAG_MIME, SignalTree } from "./SignalTree";
import { SignalTable } from "./SignalTable";
import { TrackChart } from "./TrackChart";

// IQ-F3: iba-Analyzer-style explorer over the simulated signals API --
// tree with drag & drop, unit-separated tracks or multi-axis overlay, brush
// zoom, pan, A/B cursors, event annotations and replay. IQ-F16: workbench
// chrome -- chips and segmented controls, pane-header cards, neutral notices;
// the pens keep their categorical colors (TrackChart).

const PRESETS: { label: string; ms: number | null }[] = [
  { label: "Todo", ms: null },
  { label: "1 h", ms: 3_600_000 },
  { label: "10 min", ms: 600_000 },
  { label: "1 min", ms: 60_000 },
];

const SPEEDS = [10, 60, 300];
const EVENT_MARGIN_MS = 5 * 60_000;

// Curated starting views so the demo never opens on an empty chart.
const SUGGESTED: Record<string, string[]> = {
  normal: ["injection_pressure", "screw_position", "mold_temp"],
  thermal_drift: ["mold_temp", "alarm", "dim_pins_length"],
  pressure_setpoint_change: ["holding_pressure", "injection_pressure", "process_ok", "dim_pins_length"],
  intermittent_fault_cavity_change: ["motor_current", "vibration", "alarm", "auto_mode"],
};

const SEVERITY_LABEL: Record<ProcessEventSeverity, string> = { info: "Info", warning: "Aviso", critical: "Crítico" };

// Severity as a neutral tag; warning and critical events carry their priority symbol (P2 / P1).
function SeverityTag({ severity }: { severity: ProcessEventSeverity }) {
  return (
    <span className="wb-tag shrink-0">
      {severity !== "info" && <LpSymbol priority={severity === "critical" ? 1 : 2} size={14} />}
      {SEVERITY_LABEL[severity]}
    </span>
  );
}

const toolButton = "wb-chip";

export function SignalExplorer({ scenario }: { scenario: Scenario }) {
  const [state, dispatch] = useReducer(explorerReducer, INITIAL_EXPLORER_STATE);
  const [dragOver, setDragOver] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(60);

  const tree = useAsync(fetchSignalTree, []);
  const events = useAsync(() => fetchProcessEvents(scenario.id), [scenario.id]);

  const bounds = useMemo<TimeWindow>(
    () => ({ start: Date.parse(scenario.start), end: Date.parse(scenario.end) }),
    [scenario.start, scenario.end],
  );
  const window = state.window ?? bounds;
  const span = window.end - window.start;

  const signalsById = useMemo(() => {
    const map = new Map<string, SignalInfo>();
    if (tree.data) for (const leaf of collectSignals(tree.data.root)) if (leaf.signal) map.set(leaf.signal.signal_id, leaf.signal);
    return map;
  }, [tree.data]);

  const ids = state.traces.map((t) => t.signal.signal_id);
  const series = useSeries(scenario.id, ids, state.window);
  const tracks = groupTracksByUnit(state.traces.filter((t) => t.visible));
  const activeIds = new Set(ids);
  const full = state.traces.length >= MAX_TRACES;

  // Replay: slide the window forward in time; stop at the scenario end.
  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => {
      const next = clampWindow({ start: window.start + speed * 1000, end: window.end + speed * 1000 }, bounds);
      dispatch({ type: "setWindow", window: next });
      if (next.end >= bounds.end) setPlaying(false);
    }, 1000);
    return () => clearInterval(timer);
  }, [playing, speed, window.start, window.end, bounds]);

  function setWindow(next: TimeWindow | null) {
    dispatch({ type: "setWindow", window: next ? clampWindow(next, bounds) : null });
  }

  function applyPreset(ms: number | null) {
    if (ms === null) return setWindow(null);
    const center = state.cursors.a ?? (window.start + window.end) / 2;
    setWindow({ start: center - ms / 2, end: center + ms / 2 });
  }

  function togglePlay() {
    if (!playing && state.window === null) setWindow({ start: bounds.start, end: bounds.start + 600_000 });
    setPlaying((p) => !p);
  }

  function loadSuggested() {
    const keys = SUGGESTED[scenario.id] ?? SUGGESTED.normal;
    const signals = keys
      .map((key) => signalsById.get(`L1.INY-01.${key}`))
      .filter((s): s is SignalInfo => s !== undefined);
    dispatch({ type: "addMany", signals });
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    const id = e.dataTransfer.getData(SIGNAL_DRAG_MIME) || e.dataTransfer.getData("text/plain");
    const signal = signalsById.get(id);
    if (signal) dispatch({ type: "add", signal });
  }

  const { a, b } = state.cursors;
  const sliderStep = Math.max(1, Math.round(span / 1000));

  return (
    <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
      <Card className="lg:max-h-[860px]">
        <CardHeader title="Árbol de señales" />
        {tree.loading && <p className="text-xs text-text-secondary">Cargando árbol…</p>}
        {tree.error && (
          <p role="alert" className="text-xs text-status-nok">
            {tree.error}
          </p>
        )}
        {tree.data && (
          <SignalTree root={tree.data.root} activeIds={activeIds} full={full} onAdd={(signal) => dispatch({ type: "add", signal })} />
        )}
      </Card>

      <div className="min-w-0 space-y-3">
        <Card className="space-y-2">
          <div className="flex flex-wrap items-center gap-2" role="toolbar" aria-label="Herramientas de la gráfica">
            <div className="wb-seg" role="group" aria-label="Distribución">
              <button
                type="button"
                aria-pressed={state.layout === "tracks"}
                onClick={() => dispatch({ type: "setLayout", layout: "tracks" })}
              >
                <Rows3 size={14} aria-hidden="true" /> Pistas por unidad
              </button>
              <button
                type="button"
                aria-pressed={state.layout === "overlay"}
                onClick={() => dispatch({ type: "setLayout", layout: "overlay" })}
              >
                <Layers size={14} aria-hidden="true" /> Superpuesto
              </button>
            </div>
            <button type="button" className={toolButton} aria-label="Acercar" onClick={() => setWindow(zoomWindow(window, 0.5, bounds, a ?? undefined))}>
              <ZoomIn size={14} aria-hidden="true" />
            </button>
            <button type="button" className={toolButton} aria-label="Alejar" onClick={() => setWindow(zoomWindow(window, 2, bounds))}>
              <ZoomOut size={14} aria-hidden="true" />
            </button>
            <button type="button" className={toolButton} aria-label="Desplazar a la izquierda" onClick={() => setWindow(panWindow(window, -0.5, bounds))}>
              <ChevronLeft size={14} aria-hidden="true" />
            </button>
            <button type="button" className={toolButton} aria-label="Desplazar a la derecha" onClick={() => setWindow(panWindow(window, 0.5, bounds))}>
              <ChevronRight size={14} aria-hidden="true" />
            </button>
            <button type="button" className={toolButton} aria-label="Restablecer zoom" onClick={() => setWindow(null)}>
              <RotateCcw size={14} aria-hidden="true" />
            </button>
            <div className="wb-seg" role="group" aria-label="Ventana rápida">
              {PRESETS.map((preset) => (
                <button key={preset.label} type="button" onClick={() => applyPreset(preset.ms)}>
                  {preset.label}
                </button>
              ))}
            </div>
            <span className="ml-auto font-mono text-xs text-text-primary" aria-live="polite">
              Ventana: {formatRelative(window.start, bounds.start, true)} → {formatRelative(window.end, bounds.start, true)} (
              {formatDuration(span)})
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2 border-t border-border pt-2 text-sm">
            <button type="button" className={toolButton} onClick={togglePlay} aria-label={playing ? "Pausar" : "Reproducir"}>
              {playing ? <Pause size={14} aria-hidden="true" /> : <Play size={14} aria-hidden="true" />}
              {playing ? "Pausar" : "Reproducir"}
            </button>
            <label className="wb-label inline-flex items-center gap-2">
              Velocidad
              <select
                value={speed}
                onChange={(e) => setSpeed(Number(e.target.value))}
                aria-label="Velocidad de reproducción"
                className="rounded-md border border-border bg-surface px-1.5 py-1 font-mono text-sm font-semibold normal-case tracking-normal text-text-primary"
              >
                {SPEEDS.map((s) => (
                  <option key={s} value={s}>
                    ×{s}
                  </option>
                ))}
              </select>
            </label>
            <span className="wb-tag dashed">Replay de simulación: no es telemetría en vivo.</span>
            {series.loading && <span className="text-xs text-text-secondary">Actualizando…</span>}
            {series.error && (
              <span role="alert" className="text-xs text-status-nok">
                {series.error}
              </span>
            )}
          </div>
        </Card>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = "copy";
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          data-testid="explorer-drop-zone"
          className={clsx(
            "space-y-2 rounded border-2 border-dashed p-2 transition-colors",
            dragOver ? "border-brand-accent bg-wb-selected" : "border-transparent",
          )}
        >
          {state.traces.length === 0 ? (
            <div className="flex flex-col items-center gap-3 rounded-md border border-dashed border-border bg-surface px-4 py-10 text-center">
              <p className="text-sm text-text-secondary">
                Arrastra señales desde el árbol o usa el botón <strong>+</strong> para agregarlas.
              </p>
              <button type="button" className={toolButton} onClick={loadSuggested} disabled={!tree.data}>
                <Sparkles size={14} aria-hidden="true" /> Vista sugerida para este escenario
              </button>
            </div>
          ) : tracks.length === 0 ? (
            <p className="px-2 py-6 text-center text-sm text-text-secondary">Todas las señales están ocultas.</p>
          ) : state.layout === "overlay" ? (
            <>
              {tracks.length > 3 && (
                <Notice icon={<Info size={16} aria-hidden="true" />}>
                  Hay {tracks.length} unidades distintas: para leer escalas con claridad usa «Pistas por unidad».
                </Notice>
              )}
              <TrackChart
                title={`Superpuesto · ${tracks.map((t) => t.unit).join(" / ")}`}
                traces={tracks.flatMap((t) => t.traces)}
                seriesById={series.byId}
                window={window}
                origin={bounds.start}
                cursors={state.cursors}
                events={events.data?.items ?? []}
                showEventLabels
                height={340}
                onZoom={setWindow}
                onCursor={(t) => dispatch({ type: "setCursor", cursor: state.activeCursor, time: t })}
              />
            </>
          ) : (
            tracks.map((track, index) => (
              <TrackChart
                key={track.unit}
                title={track.unit}
                traces={track.traces}
                seriesById={series.byId}
                window={window}
                origin={bounds.start}
                cursors={state.cursors}
                events={events.data?.items ?? []}
                showEventLabels={index === 0}
                height={track.traces.every((t) => t.signal.value_type === "digital") ? 90 : 170}
                onZoom={setWindow}
                onCursor={(t) => dispatch({ type: "setCursor", cursor: state.activeCursor, time: t })}
              />
            ))
          )}
        </div>
        {full && <p className="text-xs text-text-secondary">Máximo de {MAX_TRACES} señales en la gráfica.</p>}

        <Card className="space-y-3">
          <CardHeader
            title="Cursores"
            action={
              <span className="font-mono text-sm text-text-primary" aria-live="polite">
                A: {a !== null ? formatRelative(a, bounds.start, true) : "—"} · B:{" "}
                {b !== null ? formatRelative(b, bounds.start, true) : "—"} · Δt:{" "}
                {a !== null && b !== null ? formatDuration(b - a) : "—"}
              </span>
            }
          />
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <span className="text-text-secondary">Clic en la gráfica coloca el cursor:</span>
            <div className="wb-seg" role="group" aria-label="Cursor activo">
              {(["a", "b"] as const).map((id) => (
                <button
                  key={id}
                  type="button"
                  className="font-mono"
                  aria-pressed={state.activeCursor === id}
                  onClick={() => dispatch({ type: "setActiveCursor", cursor: id })}
                >
                  {id.toUpperCase()}
                </button>
              ))}
            </div>
            <button
              type="button"
              className={toolButton}
              onClick={() => {
                dispatch({ type: "setCursor", cursor: "a", time: null });
                dispatch({ type: "setCursor", cursor: "b", time: null });
              }}
            >
              Limpiar cursores
            </button>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {(["a", "b"] as const).map((id) => (
              <label key={id} className="flex items-center gap-2 font-mono text-xs font-semibold text-text-secondary">
                {id.toUpperCase()}
                <input
                  type="range"
                  className="flex-1 accent-[var(--brand-accent)]"
                  min={window.start}
                  max={window.end}
                  step={sliderStep}
                  value={state.cursors[id] ?? window.start}
                  onChange={(e) => dispatch({ type: "setCursor", cursor: id, time: Number(e.target.value) })}
                  aria-label={`Posición del cursor ${id.toUpperCase()}`}
                />
              </label>
            ))}
          </div>
          <SignalTable traces={state.traces} seriesById={series.byId} cursors={state.cursors} dispatch={dispatch} />
        </Card>

        <Card>
          <CardHeader title="Eventos del escenario" />
          {events.loading && <p className="text-xs text-text-secondary">Cargando eventos…</p>}
          {events.error && (
            <p role="alert" className="text-xs text-status-nok">
              {events.error}
            </p>
          )}
          <ol className="space-y-1.5" aria-label="Eventos del escenario">
            {events.data?.items.map((event, index) => (
              <li key={event.id} className="flex items-center gap-3 text-sm">
                <span className="w-7 shrink-0 font-mono text-xs font-semibold text-text-secondary">E{index + 1}</span>
                <span className="w-16 shrink-0 font-mono text-xs text-text-secondary">
                  {formatRelative(Date.parse(event.start), bounds.start)}
                </span>
                <span className="flex-1 text-text-primary">{event.label}</span>
                <SeverityTag severity={event.severity} />
                <button
                  type="button"
                  className={toolButton}
                  aria-label={`Ir al evento ${event.label}`}
                  onClick={() => {
                    const start = Date.parse(event.start);
                    const end = event.end ? Date.parse(event.end) : start;
                    setPlaying(false);
                    setWindow({ start: start - EVENT_MARGIN_MS, end: end + EVENT_MARGIN_MS });
                    dispatch({ type: "setCursor", cursor: "a", time: start });
                  }}
                >
                  Ir
                </button>
              </li>
            ))}
          </ol>
        </Card>
      </div>
    </div>
  );
}
