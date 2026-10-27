import { Suspense, lazy, type ComponentType } from "react";
import { Navigate, useParams } from "react-router-dom";
import { OriginBadge } from "../../components/ui/OriginBadge";
import { useDemoSession } from "../../lib/demo/DemoSessionProvider";
import type { DataOrigin } from "../../lib/demo/origin";
import { DEMO_BASE_PATH, DEMO_STEPS, type DemoStep } from "../../lib/demo/steps";
import { DEMO_DATASET_ID } from "../../lib/quality-analytics/filters";
import { ContextStep } from "./steps/ContextStep";
import { IntegrationStep } from "./steps/IntegrationStep";

// IQ-F8: chart-heavy steps load on demand, so the metrology edition (which
// never opens the demo) does not download them.
const QualityStep = lazy(() => import("./steps/QualitySteps").then((m) => ({ default: m.QualityStep })));
const DimensionalStep = lazy(() => import("./steps/QualitySteps").then((m) => ({ default: m.DimensionalStep })));
const IiotLabStep = lazy(() => import("./steps/IiotLabStep").then((m) => ({ default: m.IiotLabStep })));
const CorrelationStep = lazy(() => import("./steps/CorrelationStep").then((m) => ({ default: m.CorrelationStep })));
const AiStep = lazy(() => import("./steps/AiStep").then((m) => ({ default: m.AiStep })));

const STEP_CONTENT: Record<string, ComponentType> = {
  context: ContextStep,
  quality: QualityStep,
  dimensional: DimensionalStep,
  iiot: IiotLabStep,
  correlation: CorrelationStep,
  ai: AiStep,
  integration: IntegrationStep,
};

function StepContent({ step }: { step: DemoStep }) {
  const Content = STEP_CONTENT[step.id];
  return (
    <Suspense fallback={<p className="text-sm text-text-secondary">Cargando…</p>}>
      <Content />
    </Suspense>
  );
}

// IQ-F6: steps 2/3 analysing an imported CSV show a closed-period file, not
// the simulated dataset (the precomputed private report is hidden there too).
function stepOrigins(step: DemoStep, datasetId: string): DataOrigin[] {
  const dimensional = step.id === "quality" || step.id === "dimensional";
  return dimensional && datasetId !== DEMO_DATASET_ID ? ["HISTORICAL"] : step.origins;
}

export function DemoStepPage() {
  const { stepId } = useParams();
  const { qualityFilters } = useDemoSession();
  const step = DEMO_STEPS.find((s) => s.id === stepId);
  if (!step) {
    return <Navigate to={DEMO_BASE_PATH} replace />;
  }
  const origins = stepOrigins(step, qualityFilters.datasetId);
  return (
    <section aria-labelledby="demo-step-title" className="space-y-4">
      <div className="space-y-1">
        <p className="text-xs font-medium text-text-secondary">
          Paso {step.number} de {DEMO_STEPS.length}
        </p>
        <h2 id="demo-step-title" className="text-xl font-semibold text-text-primary">
          {step.title}
        </h2>
        <p className="text-sm text-text-secondary">{step.summary}</p>
        {origins.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-1">
            {origins.map((origin) => (
              <OriginBadge key={origin} origin={origin} />
            ))}
          </div>
        )}
      </div>
      <StepContent step={step} />
    </section>
  );
}
