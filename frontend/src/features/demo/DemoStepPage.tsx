import { Navigate, useParams } from "react-router-dom";
import { OriginBadge } from "../../components/ui/OriginBadge";
import { useDemoSession } from "../../lib/demo/DemoSessionProvider";
import type { DataOrigin } from "../../lib/demo/origin";
import { DEMO_BASE_PATH, DEMO_STEPS, type DemoStep } from "../../lib/demo/steps";
import { DEMO_DATASET_ID } from "../../lib/quality-analytics/filters";
import { ContextStep } from "./steps/ContextStep";
import { CorrelationStep } from "./steps/CorrelationStep";
import { IiotLabStep } from "./steps/IiotLabStep";
import { DimensionalStep, QualityStep } from "./steps/QualitySteps";
import { StepPlaceholder } from "./steps/StepPlaceholder";

function StepContent({ step }: { step: DemoStep }) {
  if (step.id === "context") return <ContextStep />;
  if (step.id === "quality") return <QualityStep />;
  if (step.id === "dimensional") return <DimensionalStep />;
  if (step.id === "iiot") return <IiotLabStep />;
  if (step.id === "correlation") return <CorrelationStep />;
  return <StepPlaceholder stepId={step.id} />;
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
