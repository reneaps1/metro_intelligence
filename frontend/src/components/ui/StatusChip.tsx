import { AlertOctagon, AlertTriangle, CheckCircle, Info, MinusCircle, XOctagon } from "lucide-react";
import type { RiskLevel } from "../../lib/mock/types";

export type ChipStatus = "ok" | "nok" | "warning" | "info" | "neutral" | "critical";

const CONFIG: Record<ChipStatus, { label: string; icon: typeof CheckCircle; bg: string; fg: string }> = {
  ok: { label: "OK", icon: CheckCircle, bg: "bg-status-ok-bg", fg: "text-status-ok" },
  nok: { label: "NOK", icon: XOctagon, bg: "bg-status-nok-bg", fg: "text-status-nok" },
  warning: { label: "Warning", icon: AlertTriangle, bg: "bg-status-warning-bg", fg: "text-status-warning" },
  info: { label: "Info", icon: Info, bg: "bg-status-info-bg", fg: "text-status-info" },
  neutral: { label: "No data", icon: MinusCircle, bg: "bg-status-neutral-bg", fg: "text-status-neutral" },
  critical: { label: "Critical", icon: AlertOctagon, bg: "bg-status-nok-bg", fg: "text-status-nok" },
};

export function StatusChip({ status, label }: { status: ChipStatus; label?: string }) {
  const { label: defaultLabel, icon: Icon, bg, fg } = CONFIG[status];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-xs font-medium ${bg} ${fg}`}>
      <Icon size={14} strokeWidth={2} aria-hidden="true" />
      {label ?? defaultLabel}
    </span>
  );
}

export function riskLevelToChipStatus(level: RiskLevel): ChipStatus {
  if (level === "critical") return "critical";
  if (level === "high") return "nok";
  if (level === "medium") return "warning";
  return "ok";
}
