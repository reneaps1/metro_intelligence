import { useEffect, useState } from "react";
import { getCharacteristic, getPartNumber } from "../catalog/api";
import type { Characteristic, PartNumber } from "../catalog/types";

// F5.9 (MI-38): the recommendations list only carries `characteristic_id`
// (per backend/app/schemas/intelligence.py) -- resolving the balloon
// number/name/part code for display means a lookup per unique id. Cached in
// component state (not a module-level cache) so it clears with the page,
// matching this codebase's existing no-React-Query convention (see
// lib/catalog/hooks.ts's useAsync).
export interface CharacteristicContext {
  characteristic: Characteristic;
  part: PartNumber | null;
}

export function useCharacteristicContexts(characteristicIds: string[]): Record<string, CharacteristicContext> {
  const [contexts, setContexts] = useState<Record<string, CharacteristicContext>>({});
  const key = [...new Set(characteristicIds)].sort().join(",");

  useEffect(() => {
    const ids = key ? key.split(",") : [];
    const missing = ids.filter((id) => !(id in contexts));
    if (missing.length === 0) return;

    let cancelled = false;
    Promise.all(
      missing.map(async (id) => {
        try {
          const characteristic = await getCharacteristic(id);
          const part = await getPartNumber(characteristic.part_number_id).catch(() => null);
          return [id, { characteristic, part }] as const;
        } catch {
          return null;
        }
      }),
    ).then((results) => {
      if (cancelled) return;
      setContexts((prev) => {
        const next = { ...prev };
        for (const entry of results) {
          if (entry) next[entry[0]] = entry[1];
        }
        return next;
      });
    });
    return () => {
      cancelled = true;
    };
    // `contexts`/`ids` intentionally excluded: `key` (the sorted id set) is
    // the only thing that should trigger a re-fetch of the missing entries.
  }, [key]);

  return contexts;
}
