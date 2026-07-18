import { useId, useState } from "react";
import type { ReactNode } from "react";
import { Info } from "lucide-react";

// First tooltip/popover primitive in the codebase (fix for Live Monitor's
// bare "CL" chart label, 2026-07). The only prior hover-explanation pattern
// anywhere in the app was the native `title` attribute (e.g. SignalCard's
// rationale-on-hover), which never reaches keyboard/screen-reader users --
// this opens on focus too, not just hover, for that reason.
export function InfoTooltip({ label, children }: { label: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const tooltipId = useId();

  return (
    <span className="relative inline-flex">
      <button
        type="button"
        aria-label={label}
        aria-describedby={open ? tooltipId : undefined}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(event) => {
          if (event.key === "Escape") setOpen(false);
        }}
        className="inline-flex items-center justify-center rounded-full p-1 text-text-secondary hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-primary"
      >
        <Info size={14} strokeWidth={2} aria-hidden="true" />
      </button>
      {open && (
        <span
          role="tooltip"
          id={tooltipId}
          className="absolute bottom-full left-1/2 z-overlay mb-1.5 w-56 -translate-x-1/2 rounded border border-border bg-surface-raised px-2.5 py-1.5 text-xs font-normal text-text-primary shadow-md"
        >
          {children}
        </span>
      )}
    </span>
  );
}
