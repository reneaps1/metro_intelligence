// IQ-F8: views of demo step 6. Shared by the step (its tab strip) and the
// workbench ribbon ("IA" tab), and kept in the URL (?vista=) so a view
// survives a reload and can be linked directly.

export const AI_VIEW_PARAM = "vista";
/** IQ-F12: data the lab analyses: "real" (default when available) or "sintetico". */
export const AI_DATA_PARAM = "datos";

export const AI_VIEWS = [
  { id: "modelos", label: "Modelos ML/DL", realOnly: false },
  { id: "oleadas", label: "Oleadas NOK", realOnly: false },
  { id: "cusum", label: "CUSUM", realOnly: false },
  { id: "alarmas", label: "Alarma por cavidad", realOnly: true },
  { id: "riesgo", label: "Riesgo por pieza", realOnly: true },
  { id: "what-if", label: "What-if", realOnly: false },
  { id: "fallas", label: "Fallas de máquina", realOnly: false },
] as const;

export type AiViewId = (typeof AI_VIEWS)[number]["id"];

export function parseAiView(value: string | null): AiViewId {
  return AI_VIEWS.find((v) => v.id === value)?.id ?? "modelos";
}

/** Views shown for the current data: the REAL-only studies need the real dataset. */
export function visibleAiViews(real: boolean) {
  return AI_VIEWS.filter((v) => real || !v.realOnly);
}
