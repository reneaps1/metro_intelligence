import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useDemoData } from "../../lib/mock/DataProvider";
import { StatusChip } from "../../components/ui/StatusChip";
import { Card } from "../../components/ui/Card";
import { classificationLabel, formatSpec } from "../../lib/format";

export function PartDetailPage() {
  const { partId } = useParams<{ partId: string }>();
  const { parts, characteristics, getSeries } = useDemoData();
  const part = parts.find((p) => p.id === partId);
  const partCharacteristics = characteristics.filter((c) => c.partId === partId);

  if (!part) {
    return <p className="text-text-secondary">Part not found.</p>;
  }

  return (
    <div className="space-y-4">
      <Link to="/catalog" className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary">
        <ArrowLeft size={16} /> Back to catalog
      </Link>
      <div>
        <p className="font-mono text-xs text-text-secondary">{part.code}</p>
        <h1 className="text-xl font-semibold text-text-primary">{part.name}</h1>
        <p className="text-sm text-text-secondary">{part.productFamily}</p>
      </div>
      <Card className="overflow-x-auto p-0">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border text-xs text-text-secondary">
              <th className="p-3 font-medium">Balloon</th>
              <th className="p-3 font-medium">Characteristic</th>
              <th className="p-3 font-medium">Classification</th>
              <th className="p-3 font-medium">Specification</th>
              <th className="p-3 font-medium">Latest result</th>
              <th className="p-3" />
            </tr>
          </thead>
          <tbody>
            {partCharacteristics.map((c) => {
              const series = getSeries(c.id);
              const latest = series.at(-1);
              return (
                <tr key={c.id} className="border-b border-border last:border-0 hover:bg-surface-app">
                  <td className="p-3 font-mono">{c.balloonNumber}</td>
                  <td className="p-3">
                    <span className="font-medium text-text-primary">{c.name}</span>
                    <span className="ml-2 text-xs capitalize text-text-secondary">{c.characteristicType}</span>
                  </td>
                  <td className="p-3 text-xs text-text-secondary">{classificationLabel(c.classification)}</td>
                  <td className="p-3 font-mono text-xs">{formatSpec(c.specification)}</td>
                  <td className="p-3">
                    {latest ? <StatusChip status={latest.isOk ? "ok" : "nok"} /> : <StatusChip status="neutral" />}
                  </td>
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
