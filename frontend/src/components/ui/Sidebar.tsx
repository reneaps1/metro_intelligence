import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  Activity,
  Box,
  CheckSquare,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  ShieldAlert,
  UploadCloud,
} from "lucide-react";
import clsx from "clsx";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/imports", label: "Import File", icon: UploadCloud },
  { to: "/catalog", label: "Parts & Catalog", icon: Box },
  { to: "/measurements", label: "Measurements", icon: Activity },
  { to: "/risk", label: "Risk", icon: ShieldAlert },
  { to: "/recommendations", label: "Recommendations", icon: CheckSquare },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={clsx(
        "flex h-full flex-col bg-surface-sidebar transition-[width] duration-200",
        collapsed ? "w-18" : "w-66"
      )}
    >
      <div className="flex h-14 items-center px-4">
        {!collapsed && <span className="text-sm font-semibold text-text-on-sidebar">Metro Intelligence</span>}
      </div>
      <nav className="flex-1 space-y-1 px-2">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                "flex min-h-[44px] items-center gap-3 rounded px-3 text-sm font-medium text-text-on-sidebar-muted transition-colors",
                "hover:bg-white/5 hover:text-text-on-sidebar",
                isActive && "border-l-[3px] border-brand-primary bg-white/10 pl-[9px] text-text-on-sidebar"
              )
            }
            title={collapsed ? label : undefined}
          >
            <Icon size={20} strokeWidth={2} aria-hidden="true" />
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        className="m-2 flex h-11 w-11 items-center justify-center self-end rounded text-text-on-sidebar-muted hover:bg-white/5 hover:text-text-on-sidebar"
      >
        {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
      </button>
    </aside>
  );
}
