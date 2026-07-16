import { Pause, Play } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { SCENARIO_NAMES, type ScenarioName } from "../../lib/live-monitor/types";

// LM.3 (docs/tasks/LM3-live-monitor-presenter-controls.md): presenter
// controls for the whole grid's replay session -- not a per-signal control
// (that's LM.1's grid + LM.2's detail panel). Only rendered for roles with
// `live_monitor.update` (gated by the caller, `LiveMonitorPage`), matching
// the same read-vs-decide visibility pattern already used for recommendation
// accept/reject buttons.
const SPEED_OPTIONS = [1, 5, 20];

const SCENARIO_LABELS: Record<ScenarioName, string> = {
  stable_capable: "Stable / capable",
  slow_drift: "Slow drift",
  shift_after_event: "Shift after event",
  high_variance: "High variance",
  outlier_nok: "NOK outliers",
};

export function LiveMonitorControls({
  paused,
  onTogglePause,
  speedMultiplier,
  onChangeSpeed,
  scenario,
  onChangeScenario,
  disabled,
}: {
  paused: boolean;
  onTogglePause: () => void;
  speedMultiplier: number;
  onChangeSpeed: (speed: number) => void;
  scenario: ScenarioName | null;
  onChangeScenario: (scenario: ScenarioName | null) => void;
  disabled: boolean;
}) {
  return (
    <Card className="flex flex-wrap items-center gap-4">
      <Button variant="secondary" onClick={onTogglePause} disabled={disabled}>
        {paused ? <Play size={16} aria-hidden="true" /> : <Pause size={16} aria-hidden="true" />}
        {paused ? "Play" : "Pause"}
      </Button>

      <label className="flex items-center gap-2 text-sm text-text-secondary">
        Speed
        <select
          aria-label="Playback speed"
          value={speedMultiplier}
          disabled={disabled}
          onChange={(e) => onChangeSpeed(Number(e.target.value))}
          className="min-h-[44px] rounded border border-border bg-surface px-2 text-sm text-text-primary disabled:opacity-50"
        >
          {SPEED_OPTIONS.map((speed) => (
            <option key={speed} value={speed}>
              {speed}x
            </option>
          ))}
        </select>
      </label>

      <label className="flex items-center gap-2 text-sm text-text-secondary">
        Scenario
        <select
          aria-label="Scenario"
          value={scenario ?? ""}
          onChange={(e) => onChangeScenario((e.target.value || null) as ScenarioName | null)}
          className="min-h-[44px] rounded border border-border bg-surface px-2 text-sm text-text-primary"
        >
          <option value="">Default mix</option>
          {SCENARIO_NAMES.map((name) => (
            <option key={name} value={name}>
              {SCENARIO_LABELS[name]}
            </option>
          ))}
        </select>
      </label>
    </Card>
  );
}
