import { useEffect, useMemo, useReducer, useState, type DragEvent } from "react";
import {
  ChevronLeft,
  ChevronRight,
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
import { Card } from "../../components/ui/Card";
import { StatusChip, type ChipStatus } from "../../components/ui/StatusChip";
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
import { SIGNAL_DRAG_MIME, SignalTree } from "./SignalTree";
import { SignalTable } from "./SignalTable";
import { TrackChart } from "./TrackChart";

// IQ-F3: iba-Analyzer-style explorer over the simulated signals API --
// tree with drag & drop, unit-separated tracks or multi-axis overlay, brush
// zoom, pan, A/B cursors, event annotations and replay.

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

const SEVERITY_CHIP: Record<ProcessEventSeverity, ChipStatus> = { info: "info", warning: "warning", critical: "critical" };
const SEVERITY_LABEL: Record<ProcessEventSeverity, string> = { info: "Info", warning: "Aviso", critical: "Crítico" };

const toolButton =
  "inline-flex h-8 items-center gap-1 rounded border border-border bg-surface px-2 text-xs font-medium text-text-secondary hover:border-brand-primary hover:text-text-primary disabled:opacity-40";

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
        <p className="mb-2 text-sm font-semibold text-text-primary">Árbol de señales</p>
        {tree.loading && <p className="text-xs text-text-secondary">Cargando árbol…</p>}
        {tree.error && <p className="text-xs text-status-nok">{tree.error}</p>}
        {tree.data && (
          <SignalTree root={tree.data.root} activeIds={activeIds} full={full} onAdd={(signal) => dispatch({ type: "add", signal })} />
        )}
      </Card>

      <div className="min-w-0 space-y-3">
        <Card className="space-y-2">
          <div className="flex flex-wrap items-center gap-2" role="toolbar" aria-label="Herramientas de la gráfica">
            <div className="flex rounded border border-border" role="group" aria-label="Distribución">
              <button
                type="button"
                className={clsx(toolButton, "rounded-r-none border-0", state.layout === "tracks" && "bg-surface-app text-text-primary")}
                aria-pressed={state.layout === "tracks"}
                onClick={() => dispatch({ type: "setLayout", layout: "tracks" })}
              >
                <Rows3 size={14} aria-hidden="true" /> Pistas por unidad
              </button>
              <button
                type="button"
                className={clsx(toolButton, "rounded-l-none border-0", state.layout === "overlay" && "bg-surface-app text-text-primary")}
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
            {PRESETS.map((preset) => (
              <button key={preset.label} type="button" className={toolButton} onClick={() => applyPreset(preset.ms)}>
                {preset.label}
              </button>
            ))}
            <span className="ml-auto text-xs text-text-secondary" aria-live="polite">
              Ventana: {formatRelative(window.start, bounds.start, true)} → {formatRelative(window.end, bounds.start, true)} (
              {formatDuration(span)})
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2 border-t border-border pt-2 text-xs">
            <button type="button" className={toolButton} onClick={togglePlay} aria-label={playing ? "Pausar" : "Reproducir"}>
              {playing ? <Pause size={14} aria-hidden="true" /> : <Play size={14} aria-hidden="true" />}
              {playing ? "Pausar" : "Reproducir"}
            </button>
            <label className="inline-flex items-center gap-1 text-text-secondary">
              Velocidad
              <select
                value={speed}
                onChange={(e) => setSpeed(Number(e.target.value))}
                aria-label="Velocidad de reproducción"
                className="rounded border border-border bg-surface px-1 py-1 text-text-primary"
              >
                {SPEEDS.map((s) => (
                  <option key={s} value={s}>
                    ×{s}
                  </option>
                ))}
              </select>
            </label>
            <span className="text-status-warning">Replay de simulación: no es telemetría en vivo.</span>
            {series.loading && <span className="text-text-secondary">Actualizando…</span>}
            {series.error && <span className="text-status-nok">{series.error}</span>}
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
            dragOver ? "border-brand-primary bg-surface-app" : "border-transparent",
          )}
        >
          {state.traces.length === 0 ? (
            <div className="flex flex-col items-center gap-3 rounded border border-dashed border-border px-4 py-10 text-center">
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
                <p className="text-xs text-status-warning">
                  Hay {tracks.length} unidades distintas: para leer escalas con claridad usa «Pistas por unidad».
                </p>
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
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <span className="font-semibold text-text-primary">Cursores</span>
            <span className="text-text-secondary">Clic en la gráfica coloca el cursor:</span>
            {(["a", "b"] as const).map((id) => (
              <button
                key={id}
                type="button"
                className={clsx(toolButton, state.activeCursor === id && "border-brand-primary text-text-primary")}
                aria-pressed={state.activeCursor === id}
                onClick={() => dispatch({ type: "setActiveCursor", cursor: id })}
              >
                {id.toUpperCase()}
              </button>
            ))}
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
            <span className="ml-auto font-mono text-text-primary" aria-live="polite">
              A: {a !== null ? formatRelative(a, bounds.start, true) : "—"} · B:{" "}
              {b !== null ? formatRelative(b, bounds.start, true) : "—"} · Δt:{" "}
              {a !== null && b !== null ? formatDuration(b - a) : "—"}
            </span>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {(["a", "b"] as const).map((id) => (
              <label key={id} className="flex items-center gap-2 text-xs text-text-secondary">
                {id.toUpperCase()}
                <input
                  type="range"
                  className="flex-1"
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
          <p className="mb-2 text-sm font-semibold text-text-primary">Eventos del escenario</p>
          {events.loading && <p className="text-xs text-text-secondary">Cargando eventos…</p>}
          {events.error && <p className="text-xs text-status-nok">{events.error}</p>}
          <ol className="space-y-1.5" aria-label="Eventos del escenario">
            {events.data?.items.map((event, index) => (
              <li key={event.id} className="flex items-center gap-3 text-sm">
                <span className="w-7 shrink-0 font-mono text-xs font-semibold text-text-secondary">E{index + 1}</span>
                <span className="w-16 shrink-0 font-mono text-xs text-text-secondary">
                  {formatRelative(Date.parse(event.start), bounds.start)}
                </span>
                <span className="flex-1 text-text-primary">{event.label}</span>
                <StatusChip status={SEVERITY_CHIP[event.severity]} label={SEVERITY_LABEL[event.severity]} />
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
