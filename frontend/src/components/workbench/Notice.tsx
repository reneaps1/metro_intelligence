import type { ReactNode } from "react";
import clsx from "clsx";

// IQ-F16: neutral notice of the industrial workbench (design-system.md §4.3):
// surface, icon and a left rule. `attention` adds the priority-2 rule for a
// condition the user has to act on; information never borrows status colors.

export function Notice({
  icon,
  children,
  attention = false,
  role,
  className,
}: {
  icon?: ReactNode;
  children: ReactNode;
  attention?: boolean;
  role?: "status" | "note";
  className?: string;
}) {
  return (
    <div role={role} className={clsx("wb-notice", attention && "attention", className)}>
      {icon}
      <div className="min-w-0">{children}</div>
    </div>
  );
}
