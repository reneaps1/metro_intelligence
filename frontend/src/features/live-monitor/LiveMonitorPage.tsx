import { useMemo } from "react";
import { Card } from "../../components/ui/Card";
import { listCharacteristics, listPartNumbers } from "../../lib/catalog/api";
import { useAsync } from "../../lib/catalog/hooks";
import { useCharacteristicContexts } from "../../lib/recommendations/hooks";
import { useLiveSocket } from "../../lib/live-monitor/useLiveSocket";
import type { ControlLimitsUpdatedEvent, LiveMonitorEvent, PointEvent } from "../../lib/live-monitor/types";
import { SignalCard } from "./SignalCard";

// LM.1 (docs/tasks/LM1-live-monitor-mvp.md): the panel watches a fixed-size
// set of *real* characteristics -- resolved from the catalog API, never
// hardcoded ids -- picking the first `MAX_SIGNALS` characteristics across the
// first few part numbers, the same "8-12 signals" scale the design doc
// describes for the operational dashboard mock.
const MAX_SIGNALS = 8;
const SPARKLINE_DEPTH = 30;

interface SignalState {
  points: PointEvent[];
  controlLimits: ControlLimitsUpdatedEvent | null;
}

export function aggregateEvents(events: LiveMonitorEvent[]): Record<string, SignalState> {
  const byCharacteristic: Record<string, SignalState> = {};
  for (const event of events) {
    const state = (byCharacteristic[event.characteristic_id] ??= { points: [], controlLimits: null });
    if (event.type === "point") {
      state.points.push(event);
      if (state.points.length > SPARKLINE_DEPTH) state.points.shift();
    } else {
      state.controlLimits = event;
    }
  }
  return byCharacteristic;
}

async function pickDemoCharacteristicIds(limit: number): Promise<string[]> {
  const parts = await listPartNumbers({});
  const ids: string[] = [];
  for (const part of parts.items) {
    if (ids.length >= limit) break;
    const characteristics = await listCharacteristics(part.id);
    for (const characteristic of characteristics.items) {
      if (ids.length >= limit) break;
      ids.push(characteristic.id);
    }
  }
  return ids;
}

export function LiveMonitorPage() {
  const { data: characteristicIds, loading, error } = useAsync(
    () => pickDemoCharacteristicIds(MAX_SIGNALS),
    [],
  );
  const ids = characteristicIds ?? [];
  const { events, connectionState } = useLiveSocket(ids);
  const contexts = useCharacteristicContexts(ids);
  const signals = useMemo(() => aggregateEvents(events), [events]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Live Monitor</h1>
          <p className="text-sm text-text-secondary">
            Replay of already-recorded measurements, re-evaluated live by the real Compliance/SPC
            engines -- not a prediction, not a model.
          </p>
        </div>
        <span className="text-xs font-medium text-text-secondary">
          {connectionState === "open" && "Connected"}
          {connectionState === "connecting" && "Connecting…"}
          {connectionState === "reconnecting" && "Reconnecting…"}
          {connectionState === "closed" && "Not connected"}
        </span>
      </div>

      {loading && <Card>Loading characteristics…</Card>}
      {error && <Card className="text-status-nok">{error}</Card>}
      {!loading && !error && ids.length === 0 && (
        <Card>No characteristics with an active specification were found to replay.</Card>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {ids.map((characteristicId) => {
          const context = contexts[characteristicId];
          const signal = signals[characteristicId];
          return (
            <SignalCard
              key={characteristicId}
              characteristicName={context?.characteristic.name ?? "…"}
              partCode={context?.part?.code ?? ""}
              unit={context?.characteristic.unit ?? ""}
              points={signal?.points ?? []}
              controlLimits={signal?.controlLimits ?? null}
            />
          );
        })}
      </div>
    </div>
  );
}
