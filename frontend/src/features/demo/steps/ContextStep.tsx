import { ArrowRight, BadgeCheck, Box, Flame, LayoutGrid, Ruler } from "lucide-react";
import { Card, CardHeader } from "../../../components/ui/Card";
import { OriginBadge } from "../../../components/ui/OriginBadge";
import { StatusChip, type ChipStatus } from "../../../components/ui/StatusChip";
import type { DataOrigin } from "../../../lib/demo/origin";

const FLOW = [
  {
    title: "Inyección",
    icon: Flame,
    text: "La máquina funde e inyecta el material; presiones, temperaturas y tiempos definen cada ciclo.",
  },
  {
    title: "Nido / cavidad",
    icon: LayoutGrid,
    text: "Cada disparo llena un nido; las diferencias entre nidos explican parte de la variación.",
  },
  {
    title: "Pieza",
    icon: Box,
    text: "Con trazabilidad, cada pieza hereda su ID de ciclo y de nido.",
  },
  {
    title: "Inspección dimensional",
    icon: Ruler,
    text: "Se miden cotas críticas (longitudes, posiciones) contra su tolerancia.",
  },
  {
    title: "Veredicto OK / NOK",
    icon: BadgeCheck,
    text: "La pieza se acepta o rechaza; los NOK se agrupan en el tiempo y por nido.",
  },
];

const SOURCES: {
  source: string;
  origin: DataOrigin | null;
  status: ChipStatus;
  statusLabel: string;
  note: string;
}[] = [
  {
    source: "Informe histórico de mediciones dimensionales",
    origin: "PRECOMPUTED",
    status: "ok",
    statusLabel: "Resumen disponible",
    note: "Cifras del estudio previo (período cerrado), con su definición de NOK y denominadores.",
  },
  {
    source: "Dataset dimensional de la demo",
    origin: "SIMULATED",
    status: "warning",
    statusLabel: "Sintético",
    note: "Estructura estilo cliente (nidos, turnos, lotes) con mecanismos de defecto conocidos. Pasos 2 y 3.",
  },
  {
    source: "Señales de proceso de máquina (PLC)",
    origin: "SIMULATED",
    status: "warning",
    statusLabel: "Simulación",
    note: "Sin conexión a PLC en esta demo; generador determinista y reproducible.",
  },
  {
    source: "Modelos ML / Deep Learning",
    origin: "PRECOMPUTED",
    status: "info",
    statusLabel: "Evaluación histórica",
    note: "Métricas de una evaluación previa; no es inferencia en línea.",
  },
  {
    source: "Detección de oleadas NOK / CUSUM",
    origin: "EXPERIMENTAL",
    status: "info",
    statusLabel: "Experimental",
    note: "Sin validar para control productivo.",
  },
  {
    source: "Trazabilidad ciclo ↔ pieza",
    origin: null,
    status: "neutral",
    statusLabel: "No disponible",
    note: "Requiere integración. Hoy cualquier unión proceso–medición es ilustrativa, por tiempo.",
  },
];

export function ContextStep() {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader title="Del disparo al veredicto" />
        <ol className="flex flex-col gap-2 lg:flex-row lg:items-stretch">
          {FLOW.map(({ title, icon: Icon, text }, index) => (
            <li key={title} className="flex flex-1 items-stretch gap-2">
              <div className="flex-1 rounded border border-border bg-surface-app p-3">
                <div className="mb-1 flex items-center gap-2">
                  <Icon size={18} className="text-brand-primary" aria-hidden="true" />
                  <span className="text-sm font-semibold text-text-primary">{title}</span>
                </div>
                <p className="text-xs text-text-secondary">{text}</p>
              </div>
              {index < FLOW.length - 1 && (
                <ArrowRight
                  size={18}
                  className="hidden shrink-0 self-center text-text-secondary lg:block"
                  aria-hidden="true"
                />
              )}
            </li>
          ))}
        </ol>
      </Card>

      <Card>
        <CardHeader title="Estado de las fuentes de datos" />
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-text-secondary">
              <tr>
                <th className="py-2 pr-3 font-medium">Fuente</th>
                <th className="py-2 pr-3 font-medium">Procedencia</th>
                <th className="py-2 pr-3 font-medium">Estado</th>
                <th className="py-2 font-medium">Comentario</th>
              </tr>
            </thead>
            <tbody>
              {SOURCES.map(({ source, origin, status, statusLabel, note }) => (
                <tr key={source} className="border-t border-border">
                  <td className="py-2 pr-3 font-medium text-text-primary">{source}</td>
                  <td className="py-2 pr-3">{origin ? <OriginBadge origin={origin} /> : "—"}</td>
                  <td className="py-2 pr-3">
                    <StatusChip status={status} label={statusLabel} />
                  </td>
                  <td className="py-2 text-text-secondary">{note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
