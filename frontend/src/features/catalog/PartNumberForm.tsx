import { useState, type FormEvent } from "react";
import { createPartNumber } from "../../lib/catalog/api";
import { ApiError } from "../../lib/api";
import type { ProductFamily } from "../../lib/catalog/types";
import { Card, CardHeader } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { FormField, textInputClass } from "../../components/ui/FormField";

export function PartNumberForm({
  families,
  onCreated,
  onCancel,
}: {
  families: ProductFamily[];
  onCreated: () => void;
  onCancel: () => void;
}) {
  const [productFamilyId, setProductFamilyId] = useState(families[0]?.id ?? "");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!productFamilyId || !code.trim() || !name.trim()) {
      setError("Product family, code, and name are required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await createPartNumber({
        product_family_id: productFamilyId,
        code: code.trim(),
        name: name.trim(),
        description: description.trim() || null,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to create part number. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card raised>
      <CardHeader title="New part number" />
      <form onSubmit={handleSubmit} className="space-y-3">
        <FormField label="Product family" htmlFor="pn-family">
          <select
            id="pn-family"
            value={productFamilyId}
            onChange={(e) => setProductFamilyId(e.target.value)}
            className={textInputClass()}
          >
            <option value="" disabled>
              Select a product family…
            </option>
            {families.map((family) => (
              <option key={family.id} value={family.id}>
                {family.name} ({family.code})
              </option>
            ))}
          </select>
        </FormField>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <FormField label="Code" htmlFor="pn-code">
            <input
              id="pn-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className={textInputClass()}
              placeholder="MI-DEMO-1004"
            />
          </FormField>
          <FormField label="Name" htmlFor="pn-name">
            <input id="pn-name" value={name} onChange={(e) => setName(e.target.value)} className={textInputClass()} />
          </FormField>
        </div>
        <FormField label="Description (optional)" htmlFor="pn-description">
          <input
            id="pn-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className={textInputClass()}
          />
        </FormField>
        {error && (
          <p role="alert" className="rounded bg-status-nok-bg px-3 py-2 text-sm text-status-nok">
            {error}
          </p>
        )}
        <div className="flex gap-2">
          <Button type="submit" loading={submitting} disabled={submitting}>
            Create part number
          </Button>
          <Button type="button" variant="ghost" onClick={onCancel} disabled={submitting}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  );
}
