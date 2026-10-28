// IQ-F8: views of demo step 6. Shared by the step (its tab strip) and the
// workbench ribbon ("IA" tab), and kept in the URL (?vista=) so a view
// survives a reload and can be linked directly.

export const AI_VIEW_PARAM = "vista";

export const AI_VIEWS = [
  { id: "modelos", label: "Modelos ML/DL" },
  { id: "oleadas", label: "Oleadas NOK" },
  { id: "cusum", label: "CUSUM" },
  { id: "what-if", label: "What-if" },
  { id: "fallas", label: "Fallas de máquina" },
] as const;

export type AiViewId = (typeof AI_VIEWS)[number]["id"];

export function parseAiView(value: string | null): AiViewId {
  return AI_VIEWS.find((v) => v.id === value)?.id ?? "modelos";
}
