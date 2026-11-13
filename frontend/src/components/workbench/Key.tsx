// IQ-F16: keycap for a keyboard shortcut, as on the line panel's buttons.
export function Key({ children }: { children: string }) {
  return (
    <kbd className="wb-key" aria-hidden="true">
      {children}
    </kbd>
  );
}
