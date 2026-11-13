import { Card } from "../../components/ui/Card";
import { textInputClass } from "../../components/ui/FormField";
import type { DateRange, ProcessFilters, Recipe } from "../../lib/process/types";

// Date range and recipe filter shared by the process pages. Empty dates mean
// "the last 30 days with data" (backend default); the effective range is
// always shown so the view never implies more than it covers.
export function ProcessFilterBar({
  filters,
  onChange,
  range,
  recipes,
  busy = false,
}: {
  filters: ProcessFilters;
  onChange: (next: ProcessFilters) => void;
  range: DateRange | null;
  recipes: Recipe[];
  /** True while results for the current filters are still loading. */
  busy?: boolean;
}) {
  const recipeValue = filters.recipeIds[0] ?? "";

  return (
    <Card className="flex flex-wrap items-end gap-4">
      <label className="flex flex-col gap-1 text-sm text-text-secondary" htmlFor="process-from">
        From
        <input
          id="process-from"
          type="date"
          className={textInputClass()}
          value={filters.from ?? range?.start ?? ""}
          min={range?.first_available ?? undefined}
          max={range?.last_available ?? undefined}
          onChange={(e) => onChange({ ...filters, from: e.target.value || undefined })}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm text-text-secondary" htmlFor="process-to">
        To
        <input
          id="process-to"
          type="date"
          className={textInputClass()}
          value={filters.to ?? range?.end ?? ""}
          min={range?.first_available ?? undefined}
          max={range?.last_available ?? undefined}
          onChange={(e) => onChange({ ...filters, to: e.target.value || undefined })}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm text-text-secondary" htmlFor="process-recipe">
        Recipe
        <select
          id="process-recipe"
          className={textInputClass()}
          value={recipeValue}
          onChange={(e) => onChange({ ...filters, recipeIds: e.target.value ? [e.target.value] : [] })}
        >
          <option value="">All recipes</option>
          {recipes.map((recipe) => (
            <option key={recipe.id} value={recipe.id}>
              {recipe.label}
            </option>
          ))}
        </select>
      </label>
      <p className="pb-3 text-xs font-medium text-brand-primary" role="status" aria-live="polite">
        {busy ? "Updating…" : ""}
      </p>
      {range?.first_available && range.last_available && (
        <p className="pb-3 text-xs text-text-secondary">
          Data available {range.first_available} → {range.last_available}
        </p>
      )}
    </Card>
  );
}
