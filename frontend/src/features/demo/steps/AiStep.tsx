import { useEffect, useRef, type ComponentType, type KeyboardEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { Card } from "../../../components/ui/Card";
import { useAsync } from "../../../lib/catalog/hooks";
import { AI_VIEW_PARAM, parseAiView, visibleAiViews, type AiViewId } from "../../../lib/demo/aiViews";
import { useOptionalDemoSession } from "../../../lib/demo/DemoSessionProvider";
import { storedPartId, usesReportedVerdicts } from "../../../lib/demo/part";
import { SYNTHETIC_SOURCE, type PredictiveSource } from "../../../lib/predictive/source";
import { fetchDatasets } from "../../../lib/quality-analytics/api";
import { CavityAlarms } from "../../predictive/CavityAlarms";
import { CusumPanel } from "../../predictive/CusumPanel";
import { ModelLab } from "../../predictive/ModelLab";
import { NokWaves } from "../../predictive/NokWaves";
import { PieceRisk } from "../../predictive/PieceRisk";

// IQ-F7/F8: predictive demo step -- historical ML/DL results, NOK waves,
// CUSUM and the piece-based studies, one view each (no process signals). The
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
};

export function AiStep() {
  const [params, setParams] = useSearchParams();
  const datasets = useAsync(fetchDatasets, []);
  // IQ-F22: the lab follows the part chosen in the workbench's "Pieza" control. Parts with
  // machine-reported verdicts (REAL ones and their fictitious twins) run the per-piece studies;
  // the injection demo dataset and CSV imports use the synthetic series.
  const session = useOptionalDemoSession();
  const items = datasets.data?.items ?? [];
  const stored = storedPartId();
  // Until the presenter picks a part, the same default as steps 2-3: the remembered part, else REAL.
  const selected =
    (session?.qualityFilters.datasetChosen
      ? items.find((d) => d.id === session.qualityFilters.datasetId)
      : (items.find((d) => d.id === stored && d.source_type !== "IMPORTED") ??
        items.find((d) => d.source_type === "REAL") ??
        items.find((d) => d.id === session?.qualityFilters.datasetId))) ?? null;
  const real = usesReportedVerdicts(selected) ? selected : null;
  const useReal = Boolean(real);
  const source: PredictiveSource = useReal && real ? { datasetId: real.id, real } : SYNTHETIC_SOURCE;
  const AI_VIEWS = visibleAiViews(useReal);
  const requested = parseAiView(params.get(AI_VIEW_PARAM));
  const view = AI_VIEWS.some((v) => v.id === requested) ? requested : "modelos";
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const Panel = PANELS[view];
  const ready = Boolean(datasets.data || datasets.error);
  // Tell the shell which data the lab analyses, so the step badges and the inspector say REAL.
  const setAiDatasetId = session?.setAiDatasetId;
  const realId = useReal && real && real.source_type === "REAL" ? real.id : null;
  useEffect(() => {
    setAiDatasetId?.(realId);
    return () => setAiDatasetId?.(null);
  }, [realId, setAiDatasetId]);

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
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="wb-label">Datos del laboratorio</span>
        <span className="text-sm font-semibold text-text-primary">
          {real ? real.name : "Dataset de demostración (inyección simulada)"}
        </span>
        <span className="text-xs text-text-secondary">
          Se cambia con «Pieza» en la barra. Modelos ML/DL no depende de ella.
        </span>
      </div>
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
        Lenguaje de este paso: indicio, asociación, hipótesis. Todo se calcula con las características medidas de cada
        pieza; nada aquí actúa sobre producción y todo requiere validación en planta.
      </p>
    </div>
  );
}
