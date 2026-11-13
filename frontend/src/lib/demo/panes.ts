import { useCallback, useState } from "react";

// Demo workbench: which side panes are visible. Remembered per browser only
// (a viewer convenience); storage may be unavailable, so every access is guarded.

export type PaneId = "tree" | "inspector";
export type PaneState = Record<PaneId, boolean>;

export const PANES_STORAGE_KEY = "metro-intelligence.demo.panes.v2";
const ALL_OPEN: PaneState = { tree: true, inspector: true };

function read(): PaneState {
  try {
    const raw = localStorage.getItem(PANES_STORAGE_KEY);
    if (!raw) return ALL_OPEN;
    const parsed = JSON.parse(raw) as Partial<PaneState>;
    return { tree: parsed.tree !== false, inspector: parsed.inspector !== false };
  } catch {
    return ALL_OPEN;
  }
}

function write(state: PaneState) {
  try {
    localStorage.setItem(PANES_STORAGE_KEY, JSON.stringify(state));
  } catch {
    // private mode or blocked storage: the layout still works, it just is not remembered
  }
}

export function useVisiblePanes() {
  const [visible, setVisible] = useState<PaneState>(read);
  const toggle = useCallback((pane: PaneId) => {
    setVisible((prev) => {
      const next = { ...prev, [pane]: !prev[pane] };
      write(next);
      return next;
    });
  }, []);
  return { visible, toggle };
}
