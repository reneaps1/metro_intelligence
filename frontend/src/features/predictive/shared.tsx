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

export function LoadState({ loading, error }: { loading: boolean; error: string | null }) {
  if (error) {
    return (
      <p role="alert" className="text-sm text-status-nok">
        {error}
      </p>
    );
  }
  return loading ? <p className="text-sm text-text-secondary">Cargando…</p> : null;
}
