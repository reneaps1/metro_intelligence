import { useRef, type KeyboardEvent } from "react";
import { useSearchParams } from "react-router-dom";
import clsx from "clsx";
import { Card } from "../../../components/ui/Card";
import { AI_VIEW_PARAM, AI_VIEWS, parseAiView, type AiViewId } from "../../../lib/demo/aiViews";
import { CusumPanel } from "../../predictive/CusumPanel";
import { FailurePrediction } from "../../predictive/FailurePrediction";
import { ModelLab } from "../../predictive/ModelLab";
import { NokWaves } from "../../predictive/NokWaves";
import { WhatIfPanel } from "../../predictive/WhatIfPanel";

// IQ-F7/F8: demo step 6 -- historical ML/DL results, NOK waves, CUSUM,
// what-if and the experimental failure-prediction study, one view each. The
// open view lives in the URL (?vista=) so the workbench ribbon can switch it
// and a link opens it directly. Tabs are styled as tabs (accent underline),
// not as buttons, so "Siguiente" stays the only primary action on screen.

const PANELS: Record<AiViewId, () => JSX.Element> = {
  modelos: ModelLab,
  oleadas: NokWaves,
  cusum: CusumPanel,
  "what-if": WhatIfPanel,
  fallas: FailurePrediction,
};

export function AiStep() {
  const [params, setParams] = useSearchParams();
  const view = parseAiView(params.get(AI_VIEW_PARAM));
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const Panel = PANELS[view];

  function select(id: AiViewId, focus = false) {
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set(AI_VIEW_PARAM, id);
        return next;
      },
      { replace: true },
    );
    if (focus) tabs.current[AI_VIEWS.findIndex((v) => v.id === id)]?.focus();
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const index = AI_VIEWS.findIndex((v) => v.id === view);
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      select(AI_VIEWS[event.key === "Home" ? 0 : AI_VIEWS.length - 1].id, true);
    } else if (step) {
      event.preventDefault();
      select(AI_VIEWS[(index + step + AI_VIEWS.length) % AI_VIEWS.length].id, true);
    }
  }

  return (
    <div className="space-y-4">
      <div
        role="tablist"
        aria-label="Laboratorio predictivo"
        onKeyDown={onKeyDown}
        className="flex flex-wrap gap-1 border-b border-border"
      >
        {AI_VIEWS.map((v, i) => {
          const selected = v.id === view;
          return (
            <button
              key={v.id}
              ref={(el) => {
                tabs.current[i] = el;
              }}
              id={`ai-tab-${v.id}`}
              type="button"
              role="tab"
              aria-selected={selected}
              aria-controls="ai-panel"
              tabIndex={selected ? 0 : -1}
              onClick={() => select(v.id)}
              className={clsx(
                "-mb-px min-h-[36px] border-b-2 px-3 text-sm transition-colors",
                selected
                  ? "border-brand-accent font-semibold text-text-primary"
                  : "border-transparent text-text-secondary hover:border-border hover:text-text-primary",
              )}
            >
              {v.label}
            </button>
          );
        })}
      </div>
      <Card>
        <div id="ai-panel" role="tabpanel" aria-labelledby={`ai-tab-${view}`}>
          <Panel />
        </div>
      </Card>
      <p className="text-xs text-text-secondary">
        Lenguaje de este paso: indicio, asociación, hipótesis. Nada aquí actúa sobre producción; todo requiere validación
        en planta con señales reales vinculadas a cada ciclo/pieza.
      </p>
    </div>
  );
}
