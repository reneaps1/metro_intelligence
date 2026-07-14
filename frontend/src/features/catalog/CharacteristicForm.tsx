import { useState, type FormEvent } from "react";
import { createCharacteristic } from "../../lib/catalog/api";
import { ApiError } from "../../lib/api";
import type { CharacteristicClassification } from "../../lib/catalog/types";
import { Card, CardHeader } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { FormField, textInputClass } from "../../components/ui/FormField";

export function CharacteristicForm({
  partNumberId,
  classifications,
  onCreated,
  onCancel,
}: {
  partNumberId: string;
  classifications: CharacteristicClassification[];
  onCreated: () => void;
  onCancel: () => void;
}) {
  const [balloonNumber, setBalloonNumber] = useState("");
  const [name, setName] = useState("");
  const [characteristicType, setCharacteristicType] = useState("");
  const [unit, setUnit] = useState("mm");
  const [classificationId, setClassificationId] = useState(classifications[0]?.id ?? "");
  const [nominal, setNominal] = useState("");
  const [lowerTol, setLowerTol] = useState("");
  const [upperTol, setUpperTol] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!balloonNumber.trim() || !name.trim() || !characteristicType.trim() || !unit.trim() || !classificationId) {
      setError("Balloon number, name, type, unit, and classification are required.");
      return;
    }
    if (!nominal.trim() || (!lowerTol.trim() && !upperTol.trim())) {
      setError("Nominal and at least one of lower/upper tolerance are required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await createCharacteristic({
        part_number_id: partNumberId,
        balloon_number: balloonNumber.trim(),
        name: name.trim(),
        characteristic_type: characteristicType.trim(),
        unit: unit.trim(),
        classification_id: classificationId,
        specification: {
          nominal: nominal.trim(),
          lower_tol: lowerTol.trim() || null,
          upper_tol: upperTol.trim() || null,
          unit: unit.trim(),
        },
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to create characteristic. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card raised>
      <CardHeader title="New characteristic" />
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <FormField label="Balloon number" htmlFor="ch-balloon">
            <input
              id="ch-balloon"
              value={balloonNumber}
              onChange={(e) => setBalloonNumber(e.target.value)}
              className={textInputClass()}
              placeholder="12"
            />
          </FormField>
          <FormField label="Name" htmlFor="ch-name">
            <input id="ch-name" value={name} onChange={(e) => setName(e.target.value)} className={textInputClass()} />
          </FormField>
          <FormField label="Type" htmlFor="ch-type">
            <input
              id="ch-type"
              value={characteristicType}
              onChange={(e) => setCharacteristicType(e.target.value)}
              className={textInputClass()}
              placeholder="diameter"
            />
          </FormField>
          <FormField label="Classification" htmlFor="ch-classification">
            <select
              id="ch-classification"
              value={classificationId}
              onChange={(e) => setClassificationId(e.target.value)}
              className={textInputClass()}
            >
              <option value="" disabled>
                Select a classification…
              </option>
              {classifications.map((classification) => (
                <option key={classification.id} value={classification.id}>
                  {classification.name}
                </option>
              ))}
            </select>
          </FormField>
        </div>

        <p className="text-sm font-medium text-text-primary">Initial specification</p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
          <FormField label="Nominal" htmlFor="ch-nominal">
            <input id="ch-nominal" value={nominal} onChange={(e) => setNominal(e.target.value)} className={textInputClass()} placeholder="10.000" />
          </FormField>
          <FormField label="Lower tol." htmlFor="ch-lower">
            <input id="ch-lower" value={lowerTol} onChange={(e) => setLowerTol(e.target.value)} className={textInputClass()} placeholder="-0.050" />
          </FormField>
          <FormField label="Upper tol." htmlFor="ch-upper">
            <input id="ch-upper" value={upperTol} onChange={(e) => setUpperTol(e.target.value)} className={textInputClass()} placeholder="0.050" />
          </FormField>
          <FormField label="Unit" htmlFor="ch-unit">
            <input id="ch-unit" value={unit} onChange={(e) => setUnit(e.target.value)} className={textInputClass()} />
          </FormField>
        </div>

        {error && (
          <p role="alert" className="rounded bg-status-nok-bg px-3 py-2 text-sm text-status-nok">
            {error}
          </p>
        )}
        <div className="flex gap-2">
          <Button type="submit" loading={submitting} disabled={submitting}>
            Create characteristic
          </Button>
          <Button type="button" variant="ghost" onClick={onCancel} disabled={submitting}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  );
}
