import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useDemoData } from "../../lib/mock/DataProvider";
import { cpkForCharacteristic } from "../../lib/mock/analytics";
import { TrendChart } from "../../components/charts/TrendChart";
import { Histogram } from "../../components/charts/Histogram";
import { Card, CardHeader } from "../../components/ui/Card";
import { StatTile } from "../../components/ui/StatTile";
import { classificationLabel, formatSpec } from "../../lib/format";

export function CharacteristicTrendPage() {
  const { characteristicId } = useParams<{ characteristicId: string }>();
  const { characteristics, parts, getSeries, processEvents } = useDemoData();
  const characteristic = characteristics.find((c) => c.id === characteristicId);
  const series = characteristic ? getSeries(characteristic.id) : [];

  if (!characteristic) {
    return <p className="text-text-secondary">Characteristic not found.</p>;
  }

  const part = parts.find((p) => p.id === characteristic.partId);
  const cpkValue = cpkForCharacteristic(characteristic, series);
  const nokCount = series.filter((p) => !p.isOk).length;
  const relatedEvents = processEvents.filter((e) => e.machineCode === "CMM-01" && characteristic.pattern === "shift_after_event");

  return (
    <div className="space-y-4">
      <Link to={`/catalog/${characteristic.partId}`} className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary">
        <ArrowLeft size={16} /> Back to {part?.name}
      </Link>
      <div>
        <p className="font-mono text-xs text-text-secondary">
          {part?.code} · Balloon #{characteristic.balloonNumber}
        </p>
        <h1 className="text-xl font-semibold text-text-primary">{characteristic.name}</h1>
        <p className="text-sm text-text-secondary">
          {classificationLabel(characteristic.classification)} · {formatSpec(characteristic.specification)}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Cpk (last 90d)" value={cpkValue.toFixed(2)} />
        <StatTile label="NOK results" value={`${nokCount} / ${series.length}`} />
        <StatTile label="Samples" value={String(series.length)} />
        <StatTile label="Classification" value={classificationLabel(characteristic.classification).split(" ")[0]} />
      </div>

      {relatedEvents.length > 0 && (
        <Card className="border-status-warning-bg bg-status-warning-bg">
          <p className="text-sm text-text-primary">
            <strong>Process event:</strong> {relatedEvents[0].description}
          </p>
        </Card>
      )}

      <Card>
        <CardHeader title="Trend (I-MR)" />
        <TrendChart points={series} specification={characteristic.specification} unit={characteristic.specification.unit} />
      </Card>

      <Card>
        <CardHeader title="Capability — distribution" />
        <Histogram points={series} specification={characteristic.specification} />
      </Card>
    </div>
  );
}
