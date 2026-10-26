import type { Dispatch } from "react";
import { ArrowDown, ArrowUp, X } from "lucide-react";
import {
  formatValue,
  isStepSignal,
  seriesStats,
  valueAt,
  type CursorId,
  type ExplorerAction,
  type Trace,
} from "../../lib/industrial-signals/explorer";
import type { SignalSeries } from "../../lib/industrial-signals/types";

// IQ-F3: legend + statistics table (visible / color / unit / A / B / Δ / min / max).

interface SignalTableProps {
  traces: Trace[];
  seriesById: Record<string, SignalSeries>;
  cursors: Record<CursorId, number | null>;
  dispatch: Dispatch<ExplorerAction>;
}

const iconButton =
  "flex h-7 w-7 items-center justify-center rounded text-text-secondary hover:bg-surface-app hover:text-text-primary disabled:opacity-30";

export function SignalTable({ traces, seriesById, cursors, dispatch }: SignalTableProps) {
  if (traces.length === 0) return null;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs" aria-label="Señales en la gráfica">
        <thead className="text-text-secondary">
          <tr>
            <th className="py-1 pr-2 font-medium">Ver</th>
            <th className="py-1 pr-2 font-medium">Señal</th>
            <th className="py-1 pr-2 font-medium">Unidad</th>
            <th className="py-1 pr-2 text-right font-medium">Cursor A</th>
            <th className="py-1 pr-2 text-right font-medium">Cursor B</th>
            <th className="py-1 pr-2 text-right font-medium">Δ (B−A)</th>
            <th className="py-1 pr-2 text-right font-medium">Mín.</th>
            <th className="py-1 pr-2 text-right font-medium">Máx.</th>
            <th className="py-1 pr-2 font-medium">Muestras</th>
            <th className="py-1 font-medium">
              <span className="sr-only">Acciones</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {traces.map((trace, index) => {
            const { signal } = trace;
            const series = seriesById[signal.signal_id];
            const points = series?.points ?? [];
            const step = isStepSignal(signal);
            const a = cursors.a !== null ? valueAt(points, cursors.a, step) : null;
            const b = cursors.b !== null ? valueAt(points, cursors.b, step) : null;
            const stats = seriesStats(points);
            // On a min/max envelope, interpolating between extremes is not the
            // real instantaneous value -- flag it instead of showing false precision.
            const approx = series?.mode === "envelope";
            const cursorValue = (v: number | null) => (v !== null && approx ? `≈ ${formatValue(v)}` : formatValue(v));
            const approxTitle = approx ? "Valor aproximado sobre la envolvente: acerca el zoom para leer el valor exacto" : undefined;
            return (
              <tr key={signal.signal_id} className="border-t border-border" data-testid={`row-${signal.signal_id}`}>
                <td className="py-1 pr-2">
                  <input
                    type="checkbox"
                    checked={trace.visible}
                    onChange={() => dispatch({ type: "toggle", signalId: signal.signal_id })}
                    aria-label={`Mostrar ${signal.name} ${signal.machine_code}`}
                  />
                </td>
                <td className="py-1 pr-2">
                  <span className="inline-flex items-center gap-1.5">
                    <span className="inline-block h-2 w-3 rounded-sm" style={{ background: trace.color }} aria-hidden="true" />
                    <span className={trace.visible ? "text-text-primary" : "text-text-secondary line-through"}>
                      {signal.machine_code} · {signal.name}
                    </span>
                  </span>
                </td>
                <td className="py-1 pr-2 text-text-secondary">{signal.unit}</td>
                <td className="whitespace-nowrap py-1 pr-2 text-right font-mono" title={approxTitle}>
                  {cursorValue(a)}
                </td>
                <td className="whitespace-nowrap py-1 pr-2 text-right font-mono" title={approxTitle}>
                  {cursorValue(b)}
                </td>
                <td className="whitespace-nowrap py-1 pr-2 text-right font-mono" title={approxTitle}>
                  {a !== null && b !== null ? cursorValue(b - a) : "—"}
                </td>
                <td className="py-1 pr-2 text-right font-mono">{formatValue(stats?.min)}</td>
                <td className="py-1 pr-2 text-right font-mono">{formatValue(stats?.max)}</td>
                <td className="py-1 pr-2 text-text-secondary">
                  {series ? (
                    <span title={series.mode === "envelope" ? "Envolvente mín./máx. por ciclo o tramo" : "Muestras nativas"}>
                      {series.returned_points.toLocaleString("es-MX")} / {series.native_points.toLocaleString("es-MX")}
                      {series.mode === "envelope" ? " · envolvente" : ""}
                    </span>
                  ) : (
                    "…"
                  )}
                </td>
                <td className="py-1">
                  <span className="flex">
                    <button
                      type="button"
                      className={iconButton}
                      disabled={index === 0}
                      onClick={() => dispatch({ type: "move", signalId: signal.signal_id, direction: -1 })}
                      aria-label={`Subir ${signal.name} ${signal.machine_code}`}
                    >
                      <ArrowUp size={14} aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      className={iconButton}
                      disabled={index === traces.length - 1}
                      onClick={() => dispatch({ type: "move", signalId: signal.signal_id, direction: 1 })}
                      aria-label={`Bajar ${signal.name} ${signal.machine_code}`}
                    >
                      <ArrowDown size={14} aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      className={iconButton}
                      onClick={() => dispatch({ type: "remove", signalId: signal.signal_id })}
                      aria-label={`Quitar ${signal.name} ${signal.machine_code}`}
                    >
                      <X size={14} aria-hidden="true" />
                    </button>
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
