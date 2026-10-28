import type { ReactNode } from "react";
import clsx from "clsx";
import { OriginBadge } from "../../components/ui/OriginBadge";
import type { DataOrigin } from "../../lib/demo/origin";

// IQ-F7: small building blocks shared by the predictive-lab panels.

export const axisTick = { fontSize: 11, fill: "var(--text-secondary)" };
export const tooltipStyle = {
  background: "var(--bg-surface-raised)",
  border: "1px solid var(--border-default)",
  borderRadius: 6,
  fontSize: 12,
};

export const n = (v: number, digits = 0) =>
  v.toLocaleString("es-MX", { minimumFractionDigits: digits, maximumFractionDigits: digits });

export function PanelHeader({ title, origins, children }: { title: string; origins: DataOrigin[]; children?: ReactNode }) {
  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-lg font-semibold text-text-primary">{title}</h3>
        {origins.map((o) => (
          <OriginBadge key={o} origin={o} />
        ))}
      </div>
      {children && <p className="text-sm text-text-secondary">{children}</p>}
    </div>
  );
}

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
  return (
    <div className="rounded border border-border bg-surface p-3">
      <p className="text-xs text-text-secondary">{label}</p>
      <p
        className={clsx(
          "font-mono text-xl font-semibold",
          tone === "ok" && "text-status-ok",
          tone === "nok" && "text-status-nok",
          tone === "warning" && "text-status-warning",
          !tone && "text-text-primary",
        )}
      >
        {value}
      </p>
      {hint && <p className="text-xs text-text-secondary">{hint}</p>}
    </div>
  );
}

export function Callout({ tone = "info", children }: { tone?: "info" | "warning" | "nok"; children: ReactNode }) {
  return (
    <div
      role="note"
      className={clsx(
        "rounded px-3 py-2 text-sm",
        tone === "info" && "bg-status-info-bg text-status-info",
        tone === "warning" && "bg-status-warning-bg text-status-warning",
        tone === "nok" && "bg-status-nok-bg text-status-nok",
      )}
    >
      {children}
    </div>
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
