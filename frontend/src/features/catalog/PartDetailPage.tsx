import { Fragment, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ChevronDown, ChevronRight } from "lucide-react";
import { useAuth } from "../../lib/auth/AuthProvider";
import { useAsync } from "../../lib/catalog/hooks";
import { getPartNumber, listCharacteristics, listClassifications } from "../../lib/catalog/api";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { formatSpecification } from "../../lib/catalog/format";
import { CharacteristicForm } from "./CharacteristicForm";
import { CharacteristicDetailPanel } from "./CharacteristicDetailPanel";

export function PartDetailPage() {
  const { partId } = useParams<{ partId: string }>();
  const { user } = useAuth();
  const canManage = user?.role === "admin";
  const [creating, setCreating] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const part = useAsync(() => {
    if (!partId) return Promise.reject(new Error("Missing part id"));
    return getPartNumber(partId);
  }, [partId]);
  const characteristics = useAsync(() => {
    if (!partId) return Promise.reject(new Error("Missing part id"));
    return listCharacteristics(partId);
  }, [partId]);
  const classifications = useAsync(() => listClassifications(), []);

  const classificationById = new Map((classifications.data?.items ?? []).map((c) => [c.id, c.name]));

  if (part.loading) return <p className="text-text-secondary">Loading part…</p>;
  if (part.error) return <p className="text-sm text-status-nok">{part.error}</p>;
  if (!part.data) return <p className="text-text-secondary">Part not found.</p>;

  return (
    <div className="space-y-4">
      <Link to="/catalog" className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary">
        <ArrowLeft size={16} /> Back to catalog
      </Link>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-mono text-xs text-text-secondary">{part.data.code}</p>
          <h1 className="text-xl font-semibold text-text-primary">{part.data.name}</h1>
        </div>
        {canManage && (
          <Button onClick={() => setCreating((c) => !c)}>{creating ? "Cancel" : "Add characteristic"}</Button>
        )}
      </div>

      {creating && partId && (
        <CharacteristicForm
          partNumberId={partId}
          classifications={classifications.data?.items ?? []}
          onCreated={() => {
            setCreating(false);
            characteristics.refetch();
          }}
          onCancel={() => setCreating(false)}
        />
      )}

      {characteristics.loading && characteristics.data === null && (
        <p className="text-sm text-text-secondary">Loading characteristics…</p>
      )}
      {characteristics.error && <p className="text-sm text-status-nok">{characteristics.error}</p>}

      {characteristics.data !== null && !characteristics.error && (
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-text-secondary">
                <th className="p-3 font-medium">Balloon</th>
                <th className="p-3 font-medium">Characteristic</th>
                <th className="p-3 font-medium">Classification</th>
                <th className="p-3 font-medium">Specification</th>
                <th className="p-3" />
              </tr>
            </thead>
            <tbody>
              {(characteristics.data?.items ?? []).map((c) => {
                const expanded = expandedId === c.id;
                return (
                  <Fragment key={c.id}>
                    <tr className="border-b border-border last:border-0 hover:bg-surface-app">
                      <td className="p-3 font-mono">{c.balloon_number}</td>
                      <td className="p-3">
                        <span className="font-medium text-text-primary">{c.name}</span>
                        <span className="ml-2 text-xs text-text-secondary">{c.characteristic_type}</span>
                      </td>
                      <td className="p-3 text-xs text-text-secondary">
                        {classificationById.get(c.classification_id) ?? "—"}
                      </td>
                      <td className="p-3 font-mono text-xs">
                        {c.active_specification ? formatSpecification(c.active_specification) : "No active spec"}
                      </td>
                      <td className="p-3 text-right">
                        <button
                          type="button"
                          onClick={() => setExpandedId(expanded ? null : c.id)}
                          className="inline-flex min-h-[44px] items-center gap-1 text-sm font-medium text-brand-primary hover:underline"
                        >
                          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                          {expanded ? "Hide history" : "Version history"}
                        </button>
                      </td>
                    </tr>
                    {expanded && (
                      <tr className="border-b border-border last:border-0">
                        <td colSpan={5} className="p-3">
                          <CharacteristicDetailPanel
                            characteristic={c}
                            classifications={classifications.data?.items ?? []}
                            canManage={canManage}
                            onUpdated={characteristics.refetch}
                          />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
