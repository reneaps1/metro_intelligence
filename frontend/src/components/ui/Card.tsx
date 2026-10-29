import type { ReactNode } from "react";
import clsx from "clsx";

export function Card({
  children,
  className,
  raised = false,
}: {
  children: ReactNode;
  className?: string;
  raised?: boolean;
}) {
  return (
    <div
      className={clsx(
        // ui-card / ui-card-h: hooks for the industrial workbench styles (features/demo/workbench/workbench.css).
        "ui-card rounded border border-border bg-surface p-4",
        raised && "shadow-md",
        className
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="ui-card-h mb-3 flex items-center justify-between gap-3">
      <h3 className="text-lg font-semibold text-text-primary">{title}</h3>
      {action}
    </div>
  );
}
