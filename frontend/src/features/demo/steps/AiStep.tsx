import { useState } from "react";
import { Card } from "../../../components/ui/Card";
import { CusumPanel } from "../../predictive/CusumPanel";
import { FailurePrediction } from "../../predictive/FailurePrediction";
import { ModelLab } from "../../predictive/ModelLab";
import { NokWaves } from "../../predictive/NokWaves";
import { WhatIfPanel } from "../../predictive/WhatIfPanel";

// IQ-F7: demo step 6 -- historical ML/DL results, NOK waves, CUSUM, what-if
// and the experimental failure-prediction study, one tab each so the
// presenter can follow the narrative without scrolling past everything.

const TABS = [
  { id: "models", label: "Modelos ML/DL", panel: ModelLab },
  { id: "waves", label: "Oleadas NOK", panel: NokWaves },
  { id: "cusum", label: "CUSUM", panel: CusumPanel },
  { id: "what-if", label: "What-if", panel: WhatIfPanel },
  { id: "failures", label: "Fallas de máquina", panel: FailurePrediction },
] as const;

export function AiStep() {
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("models");
  const Panel = TABS.find((t) => t.id === tab)!.panel;
  return (
    <div className="space-y-4">
      <div role="tablist" aria-label="Laboratorio predictivo" className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={t.id === tab}
            onClick={() => setTab(t.id)}
            className={
              t.id === tab
                ? "rounded border border-brand-primary bg-brand-primary px-3 py-1.5 text-sm font-medium text-text-on-brand"
                : "rounded border border-border bg-surface px-3 py-1.5 text-sm text-text-secondary hover:border-brand-primary"
            }
          >
            {t.label}
          </button>
        ))}
      </div>
      <Card>
        <div role="tabpanel">
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
