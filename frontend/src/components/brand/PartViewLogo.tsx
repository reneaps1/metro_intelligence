import clsx from "clsx";

// PartView brand (2026-11-12): an isometric part with a bored top face, flat
// two-tone in OnKaizen carbon and green. Colors come from the --pv-* tokens so
// the mark follows the light/dark theme; the source SVGs live in the design
// references folder.

export const PRODUCT_NAME = "PartView";

export function PartViewIcon({ size = 24, className }: { size?: number; className?: string }) {
  return (
    <svg
      viewBox="0 0 48 48"
      width={size}
      height={size}
      aria-hidden="true"
      focusable="false"
      className={clsx("flex-none", className)}
    >
      <path
        style={{ fill: "var(--pv-green)" }}
        fillRule="evenodd"
        d="M24 5L41 14.5L24 24L7 14.5ZM30.5 14.5a6.5 3.6 0 1 0-13 0a6.5 3.6 0 1 0 13 0Z"
      />
      <path style={{ fill: "var(--pv-ink)" }} d="M7 16.8L23 25.8V43.5L7 34.5Z" />
      <path style={{ fill: "var(--pv-gray)" }} d="M25 25.8L41 16.8V34.5L25 43.5Z" />
    </svg>
  );
}

/** "Part" in carbon, "View" in green; inherits the font size of its context. */
export function PartViewWordmark({ className }: { className?: string }) {
  return (
    <span className={clsx("font-bold tracking-tight", className)} style={{ color: "var(--pv-ink)" }}>
      Part<span style={{ color: "var(--pv-green)" }}>View</span>
    </span>
  );
}

export function PartViewLogo({ size = 28, className }: { size?: number; className?: string }) {
  return (
    <span className={clsx("inline-flex items-center gap-2", className)} aria-label={PRODUCT_NAME} role="img">
      <PartViewIcon size={size} />
      <PartViewWordmark />
    </span>
  );
}
