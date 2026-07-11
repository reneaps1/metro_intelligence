import { ArrowDown, ArrowUp } from "lucide-react";
import clsx from "clsx";
import { Card } from "./Card";
import { Sparkline } from "../charts/Sparkline";

export function StatTile({
  label,
  value,
  delta,
  sparklineValues,
}: {
  label: string;
  value: string;
  delta?: { value: string; direction: "up" | "down"; positive: boolean };
  sparklineValues?: number[];
}) {
  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-text-secondary">{label}</p>
          <p className="mt-1 font-mono text-2xl font-semibold text-text-primary">{value}</p>
          {delta && (
            <p
              className={clsx(
                "mt-1 inline-flex items-center gap-1 text-xs font-medium",
                delta.positive ? "text-status-ok" : "text-status-nok"
              )}
            >
              {delta.direction === "up" ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
              {delta.value}
            </p>
          )}
        </div>
        {sparklineValues && <Sparkline values={sparklineValues} />}
      </div>
    </Card>
  );
}
