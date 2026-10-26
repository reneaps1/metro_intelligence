import { useEffect, useState } from "react";
import { ApiError } from "../api";
import { fetchSeries } from "./api";
import type { TimeWindow } from "./explorer";
import type { SignalSeries } from "./types";

// IQ-F3: series for the explorer's current signals and window. Requests are
// debounced (zoom drags, playback) and stale responses are dropped; the
// previous data stays on screen while the next window loads.
const DEBOUNCE_MS = 120;

export interface SeriesState {
  byId: Record<string, SignalSeries>;
  loading: boolean;
  error: string | null;
}

export function useSeries(
  scenarioId: string,
  signalIds: string[],
  window: TimeWindow | null,
  maxPoints = 1200,
): SeriesState {
  const [state, setState] = useState<SeriesState>({ byId: {}, loading: false, error: null });
  const idsKey = signalIds.join(",");
  const start = window?.start;
  const end = window?.end;

  useEffect(() => {
    if (!idsKey) {
      setState({ byId: {}, loading: false, error: null });
      return;
    }
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));
    const timer = setTimeout(() => {
      fetchSeries({
        scenarioId,
        signalIds: idsKey.split(","),
        start: start !== undefined ? new Date(start).toISOString() : undefined,
        end: end !== undefined ? new Date(end).toISOString() : undefined,
        maxPoints,
      })
        .then((response) => {
          if (cancelled) return;
          const byId: Record<string, SignalSeries> = {};
          for (const series of response.series) byId[series.signal_id] = series;
          setState({ byId, loading: false, error: null });
        })
        .catch((err: unknown) => {
          if (cancelled) return;
          const message = err instanceof ApiError ? err.message : "No se pudieron cargar las señales.";
          setState((s) => ({ ...s, loading: false, error: message }));
        });
    }, DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [scenarioId, idsKey, start, end, maxPoints]);

  return state;
}
