import { weeklyRiskProxy } from "../../lib/mock/analytics";
import type { Characteristic, MeasurementPoint } from "../../lib/mock/types";

// Sequential, single-hue ramp (brand accent teal) — risk severity 0-100.
// Score is always shown as text in the cell so meaning never depends on color alone.
function cellBackground(score: number): string {
  const alpha = 0.08 + (score / 100) * 0.72;
  return `rgba(14, 124, 134, ${alpha.toFixed(2)})`;
}

function cellTextClass(score: number): string {
  return score >= 55 ? "text-white" : "text-text-primary";
}

export function RiskHeatmap({
  rows,
}: {
  rows: { characteristic: Characteristic; points: MeasurementPoint[] }[];
}) {
  const weekCount = 6;
  const weekLabels = Array.from({ length: weekCount }, (_, i) => `W-${weekCount - i}`);

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-sm">
        <caption className="sr-only">Risk proxy heatmap by characteristic over the last {weekCount} weeks</caption>
        <thead>
          <tr>
            <th scope="col" className="p-2 text-xs font-medium text-text-secondary">
              Characteristic
            </th>
            {weekLabels.map((label) => (
              <th key={label} scope="col" className="p-2 text-center text-xs font-medium text-text-secondary">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(({ characteristic, points }) => {
            const scores = weeklyRiskProxy(characteristic, points, weekCount);
            return (
              <tr key={characteristic.id} className="border-t border-border">
                <th scope="row" className="p-2 text-sm font-normal text-text-primary">
                  {characteristic.name}
                  <span className="ml-1 font-mono text-xs text-text-secondary">#{characteristic.balloonNumber}</span>
                </th>
                {scores.map((score, i) => (
                  <td key={i} className="p-1 text-center">
                    <div
                      className={`mx-auto flex h-9 w-14 items-center justify-center rounded font-mono text-xs ${cellTextClass(score)}`}
                      style={{ backgroundColor: cellBackground(score) }}
                      title={`${characteristic.name} — ${weekLabels[i]}: risk proxy ${score}`}
                    >
                      {score}
                    </div>
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="mt-3 flex items-center gap-2 text-xs text-text-secondary">
        <span>Low</span>
        {[10, 30, 50, 70, 90].map((s) => (
          <span key={s} className="h-3 w-6 rounded" style={{ backgroundColor: cellBackground(s) }} />
        ))}
        <span>High</span>
      </div>
    </div>
  );
}
