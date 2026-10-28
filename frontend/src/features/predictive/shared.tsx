import type { ReactNode } from "react";
import { AlertTriangle, Info } from "lucide-react";
import { CardHeader } from "../../components/ui/Card";
import { OriginBadge } from "../../components/ui/OriginBadge";
import { Kpi } from "../../components/workbench/Kpi";
import { Notice } from "../../components/workbench/Notice";
import type { DataOrigin } from "../../lib/demo/origin";

// IQ-F7: small building blocks shared by the predictive-lab panels.
// IQ-F16: workbench look (design-system.md §4.3) -- the panel title is the
// card's pane-header band, metrics are KPI tiles and callouts neutral notices.

export { axisTick, tooltipStyle } from "../../lib/demo/chartTheme";

export const n = (v: number, digits = 0) =>
  v.toLocaleString("es-MX", { minimumFractionDigits: digits, maximumFractionDigits: digits });

/** Chart legend text in the neutral text color (recharts paints it in the series color otherwise). */
export function legendText(text: string) {
  return <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>{text}</span>;
}

/** Select or number input inside a `wb-label` field label (undoes the label's uppercase). */
export const fieldControl =
  "ml-2 rounded-md border border-border bg-surface px-2 py-1 text-sm font-medium normal-case tracking-normal text-text-primary";

/**
 * Title of a lab panel. It is the panel's first child and the step puts the
 * panel first in its card, so the title becomes the card's pane-header band;
 * the description goes under the band.
 */
export function PanelHeader({ title, origins, children }: { title: string; origins: DataOrigin[]; children?: ReactNode }) {
  return (
    <>
      <CardHeader
        title={title}
        action={
          <div className="flex shrink-0 flex-wrap justify-end gap-1.5">
            {origins.map((o) => (
              <OriginBadge key={o} origin={o} />
            ))}
          </div>
        }
      />
      {children && <p className="text-sm text-text-secondary">{children}</p>}
    </>
  );
}

/** KPI tile. Only `tone="nok"` (NOK pieces and rates) takes the muted accent; "ok" and "warning" stay neutral. */
export function Metric({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "ok" | "nok" | "warning";
}) {
  return <Kpi label={label} value={value} hint={hint} tone={tone === "nok" ? "nok" : undefined} size="sm" />;
}

/** Neutral notice: the tone only picks the icon, since none of these asks the user to act. */
export function Callout({ tone = "info", children }: { tone?: "info" | "warning" | "nok"; children: ReactNode }) {
  const Icon = tone === "info" ? Info : AlertTriangle;
  return (
    <Notice role="note" icon={<Icon size={16} aria-hidden="true" />}>
      {children}
    </Notice>
  );
}

// Errors say what failed, the likely cause and how to recover (never a bare
// server message): a 404 here means the backend does not serve this module.
export function LoadState({
  loading,
  error,
  onRetry,
}: {
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
}) {
  if (error) {
    const notFound = /not found/i.test(error);
    return (
      <div role="alert" className="flex flex-wrap items-center gap-3 rounded bg-status-nok-bg px-3 py-2 text-sm text-status-nok">
        <p className="min-w-0 flex-1">
          <strong>No se pudo cargar este análisis.</strong>{" "}
          {notFound
            ? "El servidor no tiene este módulo: reinicie el backend con la versión actual y APP_EDITION=industrial."
            : `Detalle: ${error}`}
        </p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="min-h-[32px] rounded border border-status-nok px-3 text-sm font-medium hover:bg-surface"
          >
            Reintentar
          </button>
        )}
      </div>
    );
  }
  return loading ? (
    <p role="status" className="text-sm text-text-secondary">
      Cargando…
    </p>
  ) : null;
}
