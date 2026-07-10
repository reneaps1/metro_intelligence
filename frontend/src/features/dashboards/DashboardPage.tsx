import { useState } from "react";
import clsx from "clsx";
import { OperationalDashboard } from "./OperationalDashboard";
import { ExecutiveDashboard } from "./ExecutiveDashboard";

type Tab = "operational" | "executive";

export function DashboardPage() {
  const [tab, setTab] = useState<Tab>("operational");

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Dashboard</h1>
        <p className="text-sm text-text-secondary">Operational health and executive quality KPIs.</p>
      </div>
      <div role="tablist" aria-label="Dashboard view" className="flex gap-1 border-b border-border">
        {(["operational", "executive"] as const).map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={clsx(
              "min-h-[44px] border-b-2 px-4 text-sm font-medium capitalize",
              tab === t ? "border-brand-primary text-brand-primary" : "border-transparent text-text-secondary hover:text-text-primary"
            )}
          >
            {t}
          </button>
        ))}
      </div>
      {tab === "operational" ? <OperationalDashboard /> : <ExecutiveDashboard />}
    </div>
  );
}
