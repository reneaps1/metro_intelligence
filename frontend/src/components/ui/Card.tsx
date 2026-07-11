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
        "rounded border border-border bg-surface p-4",
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
    <div className="mb-3 flex items-center justify-between">
      <h3 className="text-lg font-semibold text-text-primary">{title}</h3>
      {action}
    </div>
  );
}
