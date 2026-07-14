import { useState, type FormEvent } from "react";
import { History } from "lucide-react";
import { useAsync } from "../../lib/catalog/hooks";
import { listSpecifications, createSpecificationVersion, updateCharacteristic } from "../../lib/catalog/api";
import { ApiError } from "../../lib/api";
import type { Characteristic, CharacteristicClassification } from "../../lib/catalog/types";
import { formatSpecification } from "../../lib/catalog/format";
import { formatDateTime } from "../../lib/format";
import { Card, CardHeader } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { StatusChip } from "../../components/ui/StatusChip";
import { FormField, textInputClass } from "../../components/ui/FormField";

function SpecificationTimeline({ characteristicId, refreshKey }: { characteristicId: string; refreshKey: number }) {
  const { data: specs, loading, error } = useAsync(
    () => listSpecifications(characteristicId),
    [characteristicId, refreshKey],
  );

  if (loading && specs === null) return <p className="text-sm text-text-secondary">Loading version history…</p>;
  if (error) return <p className="text-sm text-status-nok">{error}</p>;

  return (
    <ol className="space-y-2">
      {(specs ?? []).map((spec) => {
        const isActive = spec.valid_to === null;
        return (
          <li key={spec.id} className="flex items-start justify-between gap-3 rounded border border-border p-3">
            <div>
              <p className="font-mono text-sm text-text-primary">{formatSpecification(spec)}</p>
              <p className="mt-1 text-xs text-text-secondary">
                Effective {formatDateTime(spec.valid_from)}
                {isActive ? " — present" : ` — ${formatDateTime(spec.valid_to!)}`}
              </p>
            </div>
            <StatusChip status={isActive ? "ok" : "neutral"} label={isActive ? "Current" : "Superseded"} />
          </li>
        );
      })}
    </ol>
  );
}

function NewVersionForm({
  characteristicId,
  currentUnit,
  onCreated,
}: {
  characteristicId: string;
  currentUnit: string;
  onCreated: () => void;
}) {
  const [nominal, setNominal] = useState("");
  const [lowerTol, setLowerTol] = useState("");
  const [upperTol, setUpperTol] = useState("");
  const [unit, setUnit] = useState(currentUnit);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!nominal.trim() || (!lowerTol.trim() && !upperTol.trim())) {
      setError("Nominal and at least one of lower/upper tolerance are required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await createSpecificationVersion(characteristicId, {
        nominal: nominal.trim(),
        lower_tol: lowerTol.trim() || null,
        upper_tol: upperTol.trim() || null,
        unit: unit.trim(),
      });
      setNominal("");
      setLowerTol("");
      setUpperTol("");
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to create a new version. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2 rounded border border-dashed border-border p-3">
      <p className="text-xs text-text-secondary">
        This creates a <strong>new version</strong> effective now. The current version is preserved in history, not
        overwritten.
      </p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-4">
        <FormField label="Nominal" htmlFor="spec-nominal">
          <input id="spec-nominal" value={nominal} onChange={(e) => setNominal(e.target.value)} className={textInputClass()} placeholder="10.000" />
        </FormField>
        <FormField label="Lower tol." htmlFor="spec-lower">
          <input id="spec-lower" value={lowerTol} onChange={(e) => setLowerTol(e.target.value)} className={textInputClass()} placeholder="-0.050" />
        </FormField>
        <FormField label="Upper tol." htmlFor="spec-upper">
          <input id="spec-upper" value={upperTol} onChange={(e) => setUpperTol(e.target.value)} className={textInputClass()} placeholder="0.050" />
        </FormField>
        <FormField label="Unit" htmlFor="spec-unit">
          <input id="spec-unit" value={unit} onChange={(e) => setUnit(e.target.value)} className={textInputClass()} />
        </FormField>
      </div>
      {error && (
        <p role="alert" className="rounded bg-status-nok-bg px-3 py-2 text-sm text-status-nok">
          {error}
        </p>
      )}
      <Button type="submit" variant="secondary" loading={submitting} disabled={submitting}>
        Create new version
      </Button>
    </form>
  );
}

function EditDetailsForm({
  characteristic,
  classifications,
  onUpdated,
}: {
  characteristic: Characteristic;
  classifications: CharacteristicClassification[];
  onUpdated: () => void;
}) {
  const [name, setName] = useState(characteristic.name);
  const [characteristicType, setCharacteristicType] = useState(characteristic.characteristic_type);
  const [classificationId, setClassificationId] = useState(characteristic.classification_id);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setSaved(false);
    try {
      await updateCharacteristic(characteristic.id, {
        name: name.trim(),
        characteristic_type: characteristicType.trim(),
        classification_id: classificationId,
      });
      setSaved(true);
      onUpdated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to save changes. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2 rounded border border-border p-3">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        <FormField label="Name" htmlFor={`edit-name-${characteristic.id}`}>
          <input
            id={`edit-name-${characteristic.id}`}
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={textInputClass()}
          />
        </FormField>
        <FormField label="Type" htmlFor={`edit-type-${characteristic.id}`}>
          <input
            id={`edit-type-${characteristic.id}`}
            value={characteristicType}
            onChange={(e) => setCharacteristicType(e.target.value)}
            className={textInputClass()}
          />
        </FormField>
        <FormField label="Classification" htmlFor={`edit-classification-${characteristic.id}`}>
          <select
            id={`edit-classification-${characteristic.id}`}
            value={classificationId}
            onChange={(e) => setClassificationId(e.target.value)}
            className={textInputClass()}
          >
            {classifications.map((classification) => (
              <option key={classification.id} value={classification.id}>
                {classification.name}
              </option>
            ))}
          </select>
        </FormField>
      </div>
      {error && (
        <p role="alert" className="rounded bg-status-nok-bg px-3 py-2 text-sm text-status-nok">
          {error}
        </p>
      )}
      {saved && !error && <p className="text-sm text-status-ok">Saved.</p>}
      <Button type="submit" loading={submitting} disabled={submitting}>
        Save details
      </Button>
    </form>
  );
}

export function CharacteristicDetailPanel({
  characteristic,
  classifications,
  canManage,
  onUpdated,
}: {
  characteristic: Characteristic;
  classifications: CharacteristicClassification[];
  canManage: boolean;
  onUpdated: () => void;
}) {
  const [refreshKey, setRefreshKey] = useState(0);
  const bumpAndNotify = () => {
    setRefreshKey((k) => k + 1);
    onUpdated();
  };

  return (
    <Card className="space-y-4 bg-surface-app">
      <CardHeader
        title="Specification history"
        action={<History size={16} className="text-text-secondary" aria-hidden="true" />}
      />
      <SpecificationTimeline characteristicId={characteristic.id} refreshKey={refreshKey} />

      {canManage && (
        <>
          <NewVersionForm
            characteristicId={characteristic.id}
            currentUnit={characteristic.unit}
            onCreated={bumpAndNotify}
          />
          <div>
            <p className="mb-2 text-sm font-medium text-text-primary">Edit characteristic details</p>
            <EditDetailsForm
              characteristic={characteristic}
              classifications={classifications}
              onUpdated={bumpAndNotify}
            />
          </div>
        </>
      )}
    </Card>
  );
}
