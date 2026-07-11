import { Link } from "react-router-dom";
import { useDemoData } from "../../lib/mock/DataProvider";
import { cpkForCharacteristic } from "../../lib/mock/analytics";
import { StatusChip } from "../../components/ui/StatusChip";
import { Card } from "../../components/ui/Card";

export function MeasurementsListPage() {
  const { parts, characteristics, getSeries, measurementRuns } = useDemoData();

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Measurements</h1>
        <p className="text-sm text-text-secondary">Latest runs and characteristic-level results.</p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {measurementRuns.map((run) => {
          const part = parts.find((p) => p.id === run.partId);
          return (
            <Card key={run.id}>
              <p className="font-mono text-xs text-text-secondary">{part?.code}</p>
              <p className="font-medium text-text-primary">{part?.name}</p>
              <p className="mt-1 text-xs text-text-secondary">Machine {run.machineCode}</p>
              <div className="mt-2 flex items-center gap-2">
                <StatusChip status={run.nokCount === 0 ? "ok" : "nok"} label={`${run.nokCount} NOK / ${run.sampleCount}`} />
              </div>
            </Card>
          );
        })}
      </div>

      <Card className="overflow-x-auto p-0">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border text-xs text-text-secondary">
              <th className="p-3 font-medium">Part</th>
              <th className="p-3 font-medium">Characteristic</th>
              <th className="p-3 font-medium">Latest value</th>
              <th className="p-3 font-medium">Cpk</th>
              <th className="p-3 font-medium">Status</th>
              <th className="p-3" />
            </tr>
          </thead>
          <tbody>
            {characteristics.map((c) => {
              const part = parts.find((p) => p.id === c.partId);
              const series = getSeries(c.id);
              const latest = series.at(-1);
              const cpkValue = cpkForCharacteristic(c, series);
              return (
                <tr key={c.id} className="border-b border-border last:border-0 hover:bg-surface-app">
                  <td className="p-3 font-mono text-xs">{part?.code}</td>
                  <td className="p-3">
                    {c.name} <span className="font-mono text-xs text-text-secondary">#{c.balloonNumber}</span>
                  </td>
                  <td className="p-3 font-mono">
                    {latest ? `${latest.value.toFixed(3)} ${c.specification.unit}` : "—"}
                  </td>
                  <td className="p-3 font-mono">{cpkValue.toFixed(2)}</td>
                  <td className="p-3">{latest && <StatusChip status={latest.isOk ? "ok" : "nok"} />}</td>
                  <td className="p-3 text-right">
                    <Link to={`/measurements/${c.id}`} className="text-sm font-medium text-brand-primary hover:underline">
                      View trend
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
