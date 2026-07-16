import { useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { ChevronUp } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { useAuth } from "../../lib/auth/AuthProvider";
import { listCharacteristics, listPartNumbers } from "../../lib/catalog/api";
import { useAsync } from "../../lib/catalog/hooks";
import { useCharacteristicContexts } from "../../lib/recommendations/hooks";
import { getScenarioCandidates } from "../../lib/live-monitor/api";
import { useLiveSocket } from "../../lib/live-monitor/useLiveSocket";
import type {
  ControlLimitsUpdatedEvent,
  LiveMonitorEvent,
  PointEvent,
  ScenarioName,
} from "../../lib/live-monitor/types";
import { LiveMonitorControls } from "./LiveMonitorControls";
import { SignalCard } from "./SignalCard";
import { SignalDetailPanel } from "./SignalDetailPanel";

// LM.1 (docs/tasks/LM1-live-monitor-mvp.md): the panel watches a fixed-size
// set of *real* characteristics -- resolved from the catalog API, never
// hardcoded ids -- picking the first `MAX_SIGNALS` characteristics across the
// first few part numbers, the same "8-12 signals" scale the design doc
// describes for the operational dashboard mock.
const MAX_SIGNALS = 8;

interface SignalState {
  // LM.2 (docs/tasks/LM2-live-monitor-detail-view.md): the full replayed
  // series, not just a sparkline-sized slice -- `SignalCard` takes its own
  // preview slice, and `SignalDetailPanel` needs the whole thing. Bounded
  // upstream by `useLiveSocket`'s own MAX_RETAINED_EVENTS cap.
  points: PointEvent[];
  controlLimits: ControlLimitsUpdatedEvent | null;
}

export function aggregateEvents(events: LiveMonitorEvent[]): Record<string, SignalState> {
  const byCharacteristic: Record<string, SignalState> = {};
  for (const event of events) {
    const state = (byCharacteristic[event.characteristic_id] ??= { points: [], controlLimits: null });
    if (event.type === "point") {
      state.points.push(event);
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
  const { user } = useAuth();
  // LM.3: only roles granted `live_monitor.update` (migration 0007) can
  // steer the session -- mirrors backend/app/api/v1/live_monitor.py's RBAC,
  // and the same read-vs-decide visibility pattern already used for
  // recommendation accept/reject buttons.
  const canControl = user?.role === "quality_engineer" || user?.role === "admin";

  const { data: defaultIds, loading: defaultLoading, error: defaultError } = useAsync(
    () => pickDemoCharacteristicIds(MAX_SIGNALS),
    [],
  );
  const [scenario, setScenario] = useState<ScenarioName | null>(null);
  const {
    data: scenarioResult,
    loading: scenarioLoading,
    error: scenarioError,
  } = useAsync(
    () => (scenario ? getScenarioCandidates(scenario, MAX_SIGNALS) : Promise.resolve(null)),
    [scenario],
  );

  const ids = scenario ? (scenarioResult?.characteristic_ids ?? []) : (defaultIds ?? []);
  const loading = scenario ? scenarioLoading : defaultLoading;
  const error = scenario ? scenarioError : defaultError;

  const { events, connectionState, sendControl } = useLiveSocket(ids);
  const contexts = useCharacteristicContexts(ids);
  const signals = useMemo(() => aggregateEvents(events), [events]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const [speedMultiplier, setSpeedMultiplier] = useState(1);

  // Every fresh connection (initial connect, reconnect, or a scenario-driven
  // restart) starts a brand new server-side PlaybackControl at 1x/playing --
  // re-assert whatever the presenter had already dialed in so a dropped
  // connection or a scenario switch doesn't silently reset it.
  useEffect(() => {
    if (connectionState !== "open") return;
    if (speedMultiplier !== 1) {
      sendControl({ type: "control", action: "set_speed", speed_multiplier: speedMultiplier });
    }
    if (paused) {
      sendControl({ type: "control", action: "pause" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connectionState]);

  function togglePause() {
    const next = !paused;
    setPaused(next);
    sendControl({ type: "control", action: next ? "pause" : "resume" });
  }

  function changeSpeed(speed: number) {
    setSpeedMultiplier(speed);
    sendControl({ type: "control", action: "set_speed", speed_multiplier: speed });
  }

  function changeScenario(next: ScenarioName | null) {
    setScenario(next);
    setExpandedId(null);
  }

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
        <span
          className={clsx(
            "text-xs font-medium",
            connectionState === "denied" ? "text-status-nok" : "text-text-secondary",
          )}
        >
          {connectionState === "open" && "Connected"}
          {connectionState === "connecting" && "Connecting…"}
          {connectionState === "reconnecting" && "Reconnecting…"}
          {connectionState === "denied" && "Access denied -- missing the live_monitor.stream permission"}
          {connectionState === "closed" && "Not connected"}
        </span>
      </div>

      {canControl && (
        <LiveMonitorControls
          paused={paused}
          onTogglePause={togglePause}
          speedMultiplier={speedMultiplier}
          onChangeSpeed={changeSpeed}
          scenario={scenario}
          onChangeScenario={changeScenario}
          disabled={connectionState !== "open"}
        />
      )}

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
              selected={expandedId === characteristicId}
              onClick={() => setExpandedId(expandedId === characteristicId ? null : characteristicId)}
            />
          );
        })}
      </div>

      {expandedId && (
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <div>
              <p className="text-xs text-text-secondary">{contexts[expandedId]?.part?.code ?? ""}</p>
              <p className="font-medium text-text-primary">
                {contexts[expandedId]?.characteristic.name ?? expandedId}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setExpandedId(null)}
              className="inline-flex min-h-[44px] items-center gap-1 text-sm font-medium text-text-secondary hover:text-text-primary"
            >
              <ChevronUp size={16} aria-hidden="true" /> Hide detail
            </button>
          </div>
          <SignalDetailPanel
            characteristicId={expandedId}
            unit={contexts[expandedId]?.characteristic.unit ?? ""}
            specification={contexts[expandedId]?.characteristic.active_specification ?? null}
            points={signals[expandedId]?.points ?? []}
            controlLimits={signals[expandedId]?.controlLimits ?? null}
          />
        </Card>
      )}
    </div>
  );
}
