import type { ReactNode } from "react";

const CONTROL_CLASS =
  "min-h-[44px] w-full rounded border border-border bg-surface px-3 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-status-info";

export function FormField({
  label,
  htmlFor,
  error,
  children,
}: {
  label: string;
  htmlFor: string;
  error?: string | null;
  children: ReactNode;
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className="mb-1 block text-sm font-medium text-text-primary">
        {label}
      </label>
      {children}
      {error && (
        <p role="alert" className="mt-1 text-xs text-status-nok">
          {error}
        </p>
      )}
    </div>
  );
}

export function textInputClass(hasError?: boolean): string {
  return hasError ? `${CONTROL_CLASS} ring-2 ring-status-nok` : CONTROL_CLASS;
}
