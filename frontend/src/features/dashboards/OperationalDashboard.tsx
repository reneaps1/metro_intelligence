import { Link } from "react-router-dom";
import { useDemoData } from "../../lib/mock/DataProvider";
import { Card, CardHeader } from "../../components/ui/Card";
import { StatusChip } from "../../components/ui/StatusChip";
import { formatDateTime } from "../../lib/format";

export function OperationalDashboard() {
  const { parts, characteristics, getSeries, measurementRuns, recommendations } = useDemoData();
  const pendingRecs = recommendations.filter((r) => r.state === "pending");

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader title="Health by part" />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {parts.map((part) => {
            const chars = characteristics.filter((c) => c.partId === part.id);
            const nokCount = chars.filter((c) => getSeries(c.id).at(-1)?.isOk === false).length;
            return (
              <div key={part.id} className="rounded border border-border p-3">
                <p className="font-mono text-xs text-text-secondary">{part.code}</p>
                <p className="font-medium text-text-primary">{part.name}</p>
                <div className="mt-2">
                  <StatusChip status={nokCount === 0 ? "ok" : "nok"} label={nokCount === 0 ? "All OK" : `${nokCount} NOK`} />
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Latest runs" />
          <ul className="divide-y divide-border">
            {measurementRuns.map((run) => {
              const part = parts.find((p) => p.id === run.partId);
              return (
                <li key={run.id} className="flex items-center justify-between py-2 text-sm">
                  <div>
                    <p className="text-text-primary">{part?.name}</p>
                    <p className="text-xs text-text-secondary">
                      {run.machineCode} · {formatDateTime(run.startedAt)}
                    </p>
                  </div>
                  <StatusChip status={run.nokCount === 0 ? "ok" : "nok"} label={`${run.nokCount} NOK / ${run.sampleCount}`} />
                </li>
              );
            })}
          </ul>
        </Card>

        <Card>
          <CardHeader title="Active alerts (pending recommendations)" />
          {pendingRecs.length === 0 ? (
            <p className="text-sm text-text-secondary">No pending recommendations.</p>
          ) : (
            <ul className="divide-y divide-border">
              {pendingRecs.map((rec) => {
                const characteristic = characteristics.find((c) => c.id === rec.characteristicId);
                return (
                  <li key={rec.id} className="py-2 text-sm">
                    <Link to="/risk" className="text-text-primary hover:text-brand-primary">
                      {characteristic?.name} — {rec.type.replace(/_/g, " ")}
                    </Link>
                    <p className="text-xs text-text-secondary">risk {rec.riskScore}</p>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
