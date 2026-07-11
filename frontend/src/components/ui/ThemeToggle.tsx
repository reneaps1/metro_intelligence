import { Moon, Sun } from "lucide-react";
import { useTheme } from "../../lib/theme/ThemeProvider";

export function ThemeToggle() {
  const { resolvedTheme, setPreference } = useTheme();
  const isDark = resolvedTheme === "dark";

  return (
    <button
      type="button"
      onClick={() => setPreference(isDark ? "light" : "dark")}
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      title={isDark ? "Switch to light theme" : "Switch to dark theme"}
      className="flex h-11 w-11 items-center justify-center rounded text-text-secondary hover:bg-surface-app hover:text-text-primary"
    >
      {isDark ? <Sun size={20} /> : <Moon size={20} />}
    </button>
  );
}
