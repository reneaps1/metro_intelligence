import { useEffect, useRef, type ComponentType, type KeyboardEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { Card } from "../../../components/ui/Card";
import { useAsync } from "../../../lib/catalog/hooks";
import { AI_DATA_PARAM, AI_VIEW_PARAM, parseAiView, visibleAiViews, type AiViewId } from "../../../lib/demo/aiViews";
import { useOptionalDemoSession } from "../../../lib/demo/DemoSessionProvider";
import { SYNTHETIC_SOURCE, type PredictiveSource } from "../../../lib/predictive/source";
import { fetchDatasets } from "../../../lib/quality-analytics/api";
import { CavityAlarms } from "../../predictive/CavityAlarms";
import { CusumPanel } from "../../predictive/CusumPanel";
import { FailurePrediction } from "../../predictive/FailurePrediction";
import { ModelLab } from "../../predictive/ModelLab";
import { NokWaves } from "../../predictive/NokWaves";
import { PieceRisk } from "../../predictive/PieceRisk";
import { WhatIfPanel } from "../../predictive/WhatIfPanel";

// IQ-F7/F8: demo step 6 -- historical ML/DL results, NOK waves, CUSUM,
// what-if and the experimental failure-prediction study, one view each. The
// open view lives in the URL (?vista=) so the workbench ribbon can switch it
// and a link opens it directly. Tabs are styled as tabs (accent underline),
// not as buttons, so "Siguiente" stays the only primary action on screen.
// IQ-F16: data switch and tabs are workbench segmented controls; the panel
// sits first in its card so its title becomes the card's pane-header band.
// IQ-F12: when the customer's REAL dataset is configured locally the lab runs
// on it by default (?datos=sintetico switches back); the REAL-only studies
// (alarm per cavity, risk per piece) appear only then.

const PANELS: Record<AiViewId, ComponentType<{ source: PredictiveSource }>> = {
  modelos: ModelLab,
  oleadas: NokWaves,
  cusum: CusumPanel,
  alarmas: CavityAlarms,
  riesgo: PieceRisk,
  "what-if": WhatIfPanel,
  fallas: FailurePrediction,
};

export function AiStep() {
  const [params, setParams] = useSearchParams();
  const datasets = useAsync(fetchDatasets, []);
  const real = datasets.data?.items.find((d) => d.source_type === "REAL") ?? null;
  const useReal = Boolean(real) && params.get(AI_DATA_PARAM) !== "sintetico";
  const source: PredictiveSource = useReal && real ? { datasetId: real.id, real } : SYNTHETIC_SOURCE;
  const AI_VIEWS = visibleAiViews(useReal);
  const requested = parseAiView(params.get(AI_VIEW_PARAM));
  const view = AI_VIEWS.some((v) => v.id === requested) ? requested : "modelos";
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const Panel = PANELS[view];
  const ready = Boolean(datasets.data || datasets.error);
  // Tell the shell which data the lab analyses, so the step badges and the inspector say REAL.
  const setAiDatasetId = useOptionalDemoSession()?.setAiDatasetId;
  const realId = useReal && real ? real.id : null;
  useEffect(() => {
    setAiDatasetId?.(realId);
    return () => setAiDatasetId?.(null);
  }, [realId, setAiDatasetId]);

  function setData(value: "real" | "sintetico") {
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set(AI_DATA_PARAM, value);
        return next;
      },
      { replace: true },
    );
  }

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
      {real && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <span className="wb-label">Datos del laboratorio</span>
          <div className="wb-seg" role="group" aria-label="Datos del laboratorio">
            {(
              [
                ["real", `Reales · ${real.name.replace(/^Datos reales · /, "")}`],
                ["sintetico", "Sintéticos (demo)"],
              ] as const
            ).map(([value, label]) => (
              <button key={value} type="button" aria-pressed={(value === "real") === useReal} onClick={() => setData(value)}>
                {label}
              </button>
            ))}
          </div>
          <span className="text-xs text-text-secondary">
            Modelos ML/DL, What-if y Fallas de máquina no dependen de esta selección.
          </span>
        </div>
      )}
      <div role="tablist" aria-label="Laboratorio predictivo" onKeyDown={onKeyDown} className="wb-seg lg">
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
            >
              {v.label}
            </button>
          );
        })}
      </div>
      <div id="ai-panel" role="tabpanel" aria-labelledby={`ai-tab-${view}`}>
        <Card>
          {ready ? <Panel key={source.datasetId} source={source} /> : <p className="text-sm text-text-secondary">Cargando…</p>}
        </Card>
      </div>
      <p className="text-xs text-text-secondary">
        Lenguaje de este paso: indicio, asociación, hipótesis. Nada aquí actúa sobre producción; todo requiere validación
        en planta con señales reales vinculadas a cada ciclo/pieza.
      </p>
    </div>
  );
}
