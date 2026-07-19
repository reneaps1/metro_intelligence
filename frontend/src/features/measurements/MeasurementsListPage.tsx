import { Link } from "react-router-dom";
import { listCharacteristics, listClassifications, listPartNumbers } from "../../lib/catalog/api";
import { useAsync } from "../../lib/catalog/hooks";
import { formatSpecification } from "../../lib/catalog/format";
import { Card } from "../../components/ui/Card";

// F5.7 follow-up: migrated off useDemoData() onto the real API. Latest-value
// and Cpk columns (and the mock's "measurement runs" card grid) are
// deliberately dropped here rather than reimplemented against real data --
// either would need an N-call fan-out (getCharacteristicSeries/
// getCapabilityHistory per row) with no lazy/virtualized-row support in this
// codebase, and CharacteristicTrendPage already computes both correctly on
// the detail page this table links to.
export function MeasurementsListPage() {
  const characteristics = useAsync(() => listCharacteristics(), []);
  const parts = useAsync(() => listPartNumbers({}), []);
  const classifications = useAsync(() => listClassifications(), []);

  const partById = new Map((parts.data?.items ?? []).map((p) => [p.id, p]));
  const classificationById = new Map((classifications.data?.items ?? []).map((c) => [c.id, c.name]));

  const loading = characteristics.loading && !characteristics.data;
  const error = characteristics.error;
  const items = characteristics.data?.items ?? [];

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Measurements</h1>
        <p className="text-sm text-text-secondary">Characteristics across the catalog.</p>
      </div>

      <Card className="overflow-x-auto p-0">
        {loading ? (
          <p className="p-4 text-sm text-text-secondary">Loading…</p>
        ) : error ? (
          <p className="p-4 text-sm text-status-nok">{error}</p>
        ) : items.length === 0 ? (
          <p className="p-4 text-sm text-text-secondary">No characteristics found.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-text-secondary">
                <th className="p-3 font-medium">Part</th>
                <th className="p-3 font-medium">Characteristic</th>
                <th className="p-3 font-medium">Classification</th>
                <th className="p-3 font-medium">Specification</th>
                <th className="p-3" />
              </tr>
            </thead>
            <tbody>
              {items.map((c) => {
                const part = partById.get(c.part_number_id);
                const classificationName = classificationById.get(c.classification_id) ?? "—";
                return (
                  <tr key={c.id} className="border-b border-border last:border-0 hover:bg-surface-app">
                    <td className="p-3 font-mono text-xs">{part?.code ?? "—"}</td>
                    <td className="p-3">
                      {c.name} <span className="font-mono text-xs text-text-secondary">#{c.balloon_number}</span>
                    </td>
                    <td className="p-3">{classificationName}</td>
                    <td className="p-3 font-mono text-xs">
                      {c.active_specification ? formatSpecification(c.active_specification) : "—"}
                    </td>
                    <td className="p-3 text-right">
                      <Link
                        to={`/measurements/${c.id}`}
                        className="text-sm font-medium text-brand-primary hover:underline"
                      >
                        View trend
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
