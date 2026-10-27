import { ArrowRight, Bell, Cable, Factory, Link2, ShieldCheck, UserCheck } from "lucide-react";
import { Card, CardHeader } from "../../../components/ui/Card";
import { OriginBadge } from "../../../components/ui/OriginBadge";
import type { DataOrigin } from "../../../lib/demo/origin";

// IQ-F8: demo step 7 -- what a real integration would enable. A proposal,
// not a capability claim: every row says what the demo shows today and what
// is needed to make it real. Decisions stay with people (CLAUDE.md §2/§24).

const CHAIN = [
  { icon: Factory, title: "Máquina", text: "PLC de la inyectora, sistema iba u OPC UA: presiones, temperaturas, tiempos y alarmas." },
  { icon: Cable, title: "Conector en planta", text: "Captura on-premise, sin enviar datos fuera de la red del cliente." },
  { icon: Link2, title: "Trazabilidad ciclo ↔ pieza", text: "Cada pieza medida hereda su ID de disparo y de nido." },
  { icon: ShieldCheck, title: "Modelo validado", text: "Evaluado de forma prospectiva, en período nuevo y con métricas por episodio." },
  { icon: Bell, title: "Alertas para ingeniería", text: "Indicios con su evidencia: qué señal, qué nido, desde cuándo." },
  { icon: UserCheck, title: "Decisión humana", text: "Ingeniería acepta o descarta; nada actúa solo sobre la máquina." },
];

const TODAY: { topic: string; today: string; origin: DataOrigin; integrated: string }[] = [
  {
    topic: "Calidad dimensional",
    today: "Dataset sintético o CSV importado, analizado en memoria",
    origin: "SIMULATED",
    integrated: "Mediciones del historial con trazabilidad a pieza, programa y especificación vigente",
  },
  {
    topic: "Señales de proceso",
    today: "Generador determinista de escenarios",
    origin: "SIMULATED",
    integrated: "Señales reales de PLC/iba por ciclo, con su calidad de dato",
  },
  {
    topic: "Relación proceso–calidad",
    today: "Mecanismo impuesto (Vista B): demuestra el método, no la planta",
    origin: "SIMULATED",
    integrated: "Asociación medida sobre ciclos vinculados; hipótesis a confirmar con ensayos",
  },
  {
    topic: "Modelos ML/DL",
    today: "Métricas de un estudio histórico cerrado",
    origin: "PRECOMPUTED",
    integrated: "Modelo reentrenado con contexto de proceso y evaluado de forma prospectiva",
  },
  {
    topic: "Oleadas NOK y fallas",
    today: "Reglas y modelos experimentales sobre datos simulados",
    origin: "EXPERIMENTAL",
    integrated: "Detección temprana con precursores reales, medida por episodio y falsas alarmas por turno",
  },
];

const NEEDS = [
  "Acceso de lectura a PLC / OPC UA / iba (lista de señales, frecuencia, marcas de tiempo sincronizadas).",
  "Vínculo ciclo ↔ pieza: ID de disparo y nido en el registro de inspección.",
  "Historial de alarmas, paros y mantenimientos con su causa.",
  "Período de piloto acordado y criterio de éxito (anticipación, falsas alarmas por turno).",
  "Responsables de ingeniería que revisan y deciden sobre cada alerta.",
];

const STAGES = [
  { title: "1. Captura", text: "Conector en planta y calidad de dato de las señales." },
  { title: "2. Vinculación", text: "Trazabilidad ciclo ↔ pieza ↔ medición." },
  { title: "3. Evaluación prospectiva", text: "Modelo congelado frente a un período nuevo; métricas por episodio." },
  { title: "4. Uso supervisado", text: "Alertas a ingeniería con decisión humana y registro de cada decisión." },
];

export function IntegrationStep() {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader title="De la señal de máquina a una decisión de ingeniería" />
        <ol className="flex flex-col gap-2 lg:flex-row lg:items-stretch" aria-label="Cadena de integración">
          {CHAIN.map((step, i) => (
            <li key={step.title} className="flex flex-1 items-stretch gap-2">
              <div className="flex-1 rounded border border-border bg-surface-app p-3">
                <step.icon size={18} className="mb-1 text-brand-primary" aria-hidden="true" />
                <p className="text-sm font-semibold text-text-primary">{step.title}</p>
                <p className="text-xs text-text-secondary">{step.text}</p>
              </div>
              {i < CHAIN.length - 1 && (
                <ArrowRight size={16} className="hidden shrink-0 self-center text-text-secondary lg:block" aria-hidden="true" />
              )}
            </li>
          ))}
        </ol>
      </Card>

      <Card>
        <CardHeader title="Hoy en la demo vs. con integración" />
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm" aria-label="Hoy vs. con integración">
            <thead className="text-xs text-text-secondary">
              <tr className="border-b border-border">
                <th className="p-2 font-medium">Tema</th>
                <th className="p-2 font-medium">Hoy en la demo</th>
                <th className="p-2 font-medium">Con integración real</th>
              </tr>
            </thead>
            <tbody>
              {TODAY.map((row) => (
                <tr key={row.topic} className="border-b border-border last:border-0 align-top">
                  <td className="p-2 font-medium text-text-primary">{row.topic}</td>
                  <td className="space-y-1 p-2 text-text-secondary">
                    <OriginBadge origin={row.origin} />
                    <p>{row.today}</p>
                  </td>
                  <td className="p-2 text-text-primary">{row.integrated}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Qué haría falta de planta" />
          <ul className="list-disc space-y-1 pl-5 text-sm text-text-secondary">
            {NEEDS.map((need) => (
              <li key={need}>{need}</li>
            ))}
          </ul>
        </Card>
        <Card>
          <CardHeader title="Camino de validación" />
          <ol className="space-y-2">
            {STAGES.map((stage) => (
              <li key={stage.title} className="rounded border border-border p-2">
                <p className="text-sm font-semibold text-text-primary">{stage.title}</p>
                <p className="text-xs text-text-secondary">{stage.text}</p>
              </li>
            ))}
          </ol>
        </Card>
      </div>

      <blockquote className="rounded border-l-4 border-brand-primary bg-status-info-bg px-4 py-3 text-sm text-text-primary">
        Metro Intelligence conecta mediciones dimensionales y contexto de proceso en un mismo lugar para pasar de
        visualizar los NOK a investigar sus patrones, generar hipótesis y evaluar anticipadamente riesgos. La capa IIoT
        mostrada aquí es simulada: para validar causalidad y predicción necesitamos capturar señales reales de máquina,
        vincularlas a cada ciclo/pieza y evaluar modelos prospectivamente.
      </blockquote>
      <p className="text-xs text-text-secondary">
        Principios: todo corre on-premise y nada sale de la red del cliente por defecto; la plataforma no ajusta máquinas,
        no libera ni rechaza piezas por sí sola; cada alerta guarda su evidencia y cada decisión humana queda registrada.
      </p>
    </div>
  );
}
