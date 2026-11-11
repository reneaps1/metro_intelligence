import { useAsync } from "../catalog/hooks";
import { fetchDataset } from "./api";
import type { QualityDataset } from "./types";

/**
 * IQ-F22: the full dataset for `id`. Taken from `listed` when the plain list already has it
 * (synthetic, twins, imports, legacy REAL); otherwise fetched once (private parts of the registry).
 */
export function useDataset(id: string | null, listed: QualityDataset[] | null) {
  const inList = id ? (listed?.find((d) => d.id === id) ?? null) : null;
  const fetched = useAsync(
    () => (id && listed && !inList ? fetchDataset(id) : Promise.resolve(null)),
    [id, Boolean(listed), Boolean(inList)],
  );
  return {
    dataset: inList ?? (fetched.data && fetched.data.id === id ? fetched.data : null),
    loading: !inList && fetched.loading,
    error: inList ? null : fetched.error,
  };
}
