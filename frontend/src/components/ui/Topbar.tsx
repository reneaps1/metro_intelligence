import { useState } from "react";
import { useLocation } from "react-router-dom";
import { Bell, UserCircle } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import { useAuth } from "../../lib/auth/AuthProvider";
import { useDemoData } from "../../lib/mock/DataProvider";

const SECTION_LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  imports: "Import File",
  catalog: "Parts & Catalog",
  measurements: "Measurements",
  risk: "Risk & Recommendations",
};

export function Topbar() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { recommendations } = useDemoData();
  const [menuOpen, setMenuOpen] = useState(false);
  const pendingCount = recommendations.filter((r) => r.state === "pending").length;

  const section = location.pathname.split("/")[1] || "dashboard";
  const label = SECTION_LABELS[section] ?? "Metro Intelligence";

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-surface px-4">
      <nav aria-label="Breadcrumb" className="text-sm text-text-secondary">
        <span className="text-text-primary">{label}</span>
      </nav>
      <div className="flex items-center gap-1">
        <ThemeToggle />
        <button
          type="button"
          aria-label={`Notifications, ${pendingCount} pending`}
          title={`${pendingCount} pending recommendations`}
          className="relative flex h-11 w-11 items-center justify-center rounded text-text-secondary hover:bg-surface-app hover:text-text-primary"
        >
          <Bell size={20} />
          {pendingCount > 0 && (
            <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-status-nok px-1 text-[10px] font-semibold text-white">
              {pendingCount}
            </span>
          )}
        </button>
        <div className="relative">
          <button
            type="button"
            onClick={() => setMenuOpen((o) => !o)}
            className="flex min-h-[44px] items-center gap-2 rounded px-2 text-sm text-text-primary hover:bg-surface-app"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
          >
            <UserCircle size={22} />
            <span className="hidden sm:inline">{user?.displayName ?? "Guest"}</span>
          </button>
          {menuOpen && (
            <div
              role="menu"
              className="absolute right-0 z-dropdown mt-1 w-56 rounded border border-border bg-surface-raised p-2 shadow-md"
            >
              <p className="px-2 py-1 text-xs text-text-secondary">Signed in as</p>
              <p className="px-2 pb-2 text-sm font-medium text-text-primary">{user?.email}</p>
              <p className="px-2 pb-2 text-xs capitalize text-brand-accent">{user?.role.replace("_", " ")}</p>
              <button
                type="button"
                role="menuitem"
                onClick={logout}
                className="min-h-[44px] w-full rounded px-2 text-left text-sm text-status-nok hover:bg-status-nok-bg"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
