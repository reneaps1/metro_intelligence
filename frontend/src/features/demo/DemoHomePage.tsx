import { useNavigate } from "react-router-dom";
import { Brain, Crosshair, MonitorDot, Play } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { Card, CardHeader } from "../../components/ui/Card";
import { OriginLegend } from "../../components/ui/OriginBadge";
import { DATA_ORIGINS } from "../../lib/demo/origin";
import { DEMO_BASE_PATH, DEMO_STEPS, LINE_PANEL_PATH, stepPath } from "../../lib/demo/steps";

const QUICK_ACCESS = [
  {
    label: "Ver problema del nido crítico",
    description: "Concentración de NOK por nido, con denominador y período.",
    icon: Crosshair,
    step: "quality",
  },
  {
    label: "Mostrar limitaciones del modelo ML",
    description: "Falsas alarmas, precisión baja y por qué no hay rechazo automático.",
    icon: Brain,
    step: "ai",
  },
] as const;

export function DemoHomePage() {
  const navigate = useNavigate();
  const firstStep = DEMO_STEPS[0];

  return (
    <div className="space-y-4">
      <Card raised className="space-y-4">
        <p className="max-w-3xl text-base text-text-primary">
          Mediciones dimensionales y contexto de proceso en un mismo lugar: pasar de <strong>ver</strong> los NOK a{" "}
          <strong>investigar</strong> sus patrones, generar hipótesis y evaluar riesgos con anticipación.
        </p>
        <p className="max-w-3xl text-sm text-text-secondary">
          Todo se calcula con las <strong>características medidas de cada pieza</strong>: dimensiones, tolerancias,
          nido, turno y veredicto OK/NOK.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => navigate(stepPath(firstStep))}>
            <Play size={16} aria-hidden="true" />
            Iniciar demo
          </Button>
          <Button variant="secondary" onClick={() => navigate(LINE_PANEL_PATH)}>
            <MonitorDot size={16} aria-hidden="true" />
            Panel de calidad en línea
          </Button>
        </div>
      </Card>

      <section aria-labelledby="quick-access-title" className="space-y-2">
        <h2 id="quick-access-title" className="wb-label">
          Accesos rápidos
        </h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {QUICK_ACCESS.map(({ label, description, icon: Icon, step }) => (
            <button
              key={label}
              type="button"
              onClick={() => navigate(`${DEMO_BASE_PATH}/${step}`)}
              className="flex items-start gap-3 rounded-md border border-border bg-surface p-4 text-left transition-colors hover:border-brand-accent"
            >
              <Icon size={20} className="mt-0.5 shrink-0 text-text-secondary" aria-hidden="true" />
              <span>
                <span className="block text-sm font-semibold text-text-primary">{label}</span>
                <span className="block text-xs text-text-secondary">{description}</span>
              </span>
            </button>
          ))}
        </div>
      </section>

      <Card>
        <CardHeader title="Cómo leer el origen de cada dato" />
        <OriginLegend origins={DATA_ORIGINS} />
      </Card>
    </div>
  );
}
