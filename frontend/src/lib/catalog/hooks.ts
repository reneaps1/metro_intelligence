import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api";

// F5.5 (MI-34): small shared fetch-state hook. No React Query/SWR dependency
// -- this codebase has none yet, and one hook covers what these screens need
// (loading/error/refetch), matching the project's "no speculative
// abstraction" rule.
export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useAsync<T>(fetcher: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetcher()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // `fetcher` is intentionally excluded: callers pass a fresh closure each
    // render, so depending on it would refetch every render. `deps` is the
    // caller's explicit list of what should actually trigger a refetch.
  }, [...deps, tick]);

  return { data, loading, error, refetch };
}
