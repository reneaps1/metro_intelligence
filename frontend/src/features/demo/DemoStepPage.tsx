import { Suspense, lazy, type ComponentType } from "react";
import { Navigate, useParams } from "react-router-dom";
import { OriginBadge } from "../../components/ui/OriginBadge";
import { useDemoSession } from "../../lib/demo/DemoSessionProvider";
import { stepOrigins } from "../../lib/demo/stepOrigins";
import { DEMO_BASE_PATH, DEMO_STEPS, type DemoStep } from "../../lib/demo/steps";
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

// The step header is the only place that titles the view; the workbench
// toolbar shows where it sits in the walkthrough (n / 7).
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
      <div className="flex flex-wrap items-start gap-x-6 gap-y-2">
        <div className="min-w-0 flex-1 space-y-0.5">
          <h2 id="demo-step-title" className="text-xl font-semibold text-text-primary">
            {step.title}
          </h2>
          <p className="text-sm text-text-secondary">{step.summary}</p>
        </div>
        {origins.length > 0 && (
          <div className="flex flex-wrap items-center gap-2" aria-label="Procedencia de los datos de esta vista">
            <span className="text-xs text-text-secondary">Datos</span>
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
