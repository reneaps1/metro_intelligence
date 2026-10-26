import { Construction } from "lucide-react";
import { Card } from "../../../components/ui/Card";

// IQ-F1: honest placeholder for steps whose content lands in later phases of
// docs/tasks/IQ-plan-demo-industrial-quality.md -- no fake charts.
const PLANNED: Record<string, { phase: string; items: string[] }> = {
  quality: {
    phase: "F5",
    items: [
      "KPIs: piezas, mediciones, OK/NOK y tasa NOK con denominador y período",
      "Tendencia de NOK por día, hora y turno",
      "Pareto de defectos y tasa NOK por nido",
      "Heatmap nido × variable",
    ],
  },
  dimensional: {
    phase: "F5–F6",
    items: [
      "Selector de variable dimensional, histograma y boxplot",
      "Límites de especificación frente a límites de control (SPC)",
      "Comparativos por nido, turno y máquina",
      "Carga de CSV con mapeo de columnas",
    ],
  },
  ai: {
    phase: "F7",
    items: [
      "Comparativa Gradient Boosting vs. MLP: ROC-AUC, PR-AUC, recall y precisión",
      "Matrices de confusión y costo de las falsas alarmas",
      "Oleadas NOK: detectar una racha iniciada no es predecir su inicio",
      "CUSUM experimental y simulación what-if hipotética",
    ],
  },
  integration: {
    phase: "F8",
    items: [
      "Conectividad PLC / OPC UA / iba",
      "Trazabilidad por ciclo y pieza",
      "Validación prospectiva de modelos",
      "Alertas para ingeniería con decisión humana",
    ],
  },
};

export function StepPlaceholder({ stepId }: { stepId: string }) {
  const planned = PLANNED[stepId];
  if (!planned) return null;
  return (
    <Card className="space-y-3">
      <p className="flex items-center gap-2 text-sm font-medium text-status-warning">
        <Construction size={16} aria-hidden="true" />
        En construcción: esta sección se completa en la fase {planned.phase} del plan.
      </p>
      <div>
        <p className="mb-1 text-sm font-semibold text-text-primary">Contenido previsto</p>
        <ul className="list-disc space-y-1 pl-5 text-sm text-text-secondary">
          {planned.items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </Card>
  );
}
