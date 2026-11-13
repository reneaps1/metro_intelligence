import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import type { ProcessFilters } from "./types";

// Date range and recipes live in the URL so a filtered view can be
// bookmarked, shared, and survives navigating to a step and back.
export function useProcessFilters(): [ProcessFilters, (next: ProcessFilters) => void] {
  const [params, setParams] = useSearchParams();
  const from = params.get("from") ?? undefined;
  const to = params.get("to") ?? undefined;
  const recipeKey = params.getAll("recipe").join(",");

  const filters = useMemo<ProcessFilters>(
    () => ({ from, to, recipeIds: recipeKey ? recipeKey.split(",") : [] }),
    [from, to, recipeKey],
  );

  const setFilters = useCallback(
    (next: ProcessFilters) => {
      const updated = new URLSearchParams();
      if (next.from) updated.set("from", next.from);
      if (next.to) updated.set("to", next.to);
      next.recipeIds.forEach((id) => updated.append("recipe", id));
      setParams(updated, { replace: true });
    },
    [setParams],
  );

  return [filters, setFilters];
}

export function filtersSearch(filters: ProcessFilters): string {
  const params = new URLSearchParams();
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  filters.recipeIds.forEach((id) => params.append("recipe", id));
  const text = params.toString();
  return text ? `?${text}` : "";
}
