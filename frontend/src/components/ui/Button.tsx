import type { ButtonHTMLAttributes } from "react";
import clsx from "clsx";

type Variant = "primary" | "secondary" | "danger" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
}

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: "bg-brand-primary text-text-on-brand hover:bg-brand-primary-hover",
  secondary: "border border-border bg-surface text-text-primary hover:bg-surface-app",
  danger: "bg-status-nok text-white hover:opacity-90",
  ghost: "text-text-secondary hover:bg-surface-app",
};

export function Button({ variant = "primary", loading = false, className, disabled, children, ...rest }: ButtonProps) {
  return (
    <button
      className={clsx(
        "inline-flex min-h-[44px] items-center justify-center gap-2 rounded px-4 text-sm font-medium transition-colors duration-150",
        "disabled:cursor-not-allowed disabled:opacity-50",
        VARIANT_CLASSES[variant],
        className
      )}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden="true" />
      )}
      {children}
    </button>
  );
}
