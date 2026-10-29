import { useCallback, useState, type KeyboardEvent, type ReactNode } from "react";
import { Check } from "lucide-react";
import clsx from "clsx";
import { usePopover } from "./usePopover";

// Menu bar of the demo workbench (design-system.md §4.1). It is the index of
// every command (HIG: everything reachable from a menu); the commands also
// shown in the toolbar open the same controls instead of duplicating them.

export type MenuEntry =
  | { separator: true }
  | { label: string; onSelect?: () => void; checked?: boolean; shortcut?: string; disabled?: boolean };

export interface Menu {
  id: string;
  label: string;
  entries: MenuEntry[];
}

export function MenuBar({ menus, trailing }: { menus: Menu[]; trailing?: ReactNode }) {
  const [openId, setOpenId] = useState<string | null>(null);
  const close = useCallback(() => setOpenId(null), []);
  const ref = usePopover(openId !== null, close);

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (openId === null || (event.key !== "ArrowRight" && event.key !== "ArrowLeft")) return;
    event.preventDefault();
    const index = menus.findIndex((m) => m.id === openId);
    const step = event.key === "ArrowRight" ? 1 : -1;
    setOpenId(menus[(index + step + menus.length) % menus.length].id);
  }

  return (
    <div
      ref={ref}
      role="menubar"
      aria-label="Menú principal"
      onKeyDown={onKeyDown}
      className="flex min-h-[32px] flex-none flex-wrap items-center gap-0.5 border-b border-border bg-wb-chrome px-2 text-[13px] text-wb-chrome-text"
    >
      <span
        aria-hidden="true"
        className="mr-2 flex h-5 w-5 items-center justify-center rounded-sm bg-brand-accent font-mono text-[11px] font-semibold text-text-on-brand"
      >
        M
      </span>
      {menus.map((menu) => {
        const open = menu.id === openId;
        return (
          <div key={menu.id} className="relative">
            <button
              type="button"
              role="menuitem"
              aria-haspopup="menu"
              aria-expanded={open}
              onClick={() => setOpenId(open ? null : menu.id)}
              className={clsx(
                "h-7 rounded-sm px-2.5 text-text-primary hover:bg-wb-pane-header",
                open && "bg-wb-selected",
              )}
            >
              {menu.label}
            </button>
            {open && (
              <div
                role="menu"
                aria-label={menu.label}
                className="absolute left-0 top-full z-dropdown mt-0.5 min-w-[280px] rounded-sm border border-border bg-surface-raised p-1 text-text-primary shadow-md"
              >
                {menu.entries.map((entry, i) =>
                  "separator" in entry ? (
                    <div key={`sep-${i}`} role="separator" className="mx-1.5 my-1 h-px bg-border" />
                  ) : (
                    <button
                      key={entry.label}
                      type="button"
                      role={entry.checked === undefined ? "menuitem" : "menuitemcheckbox"}
                      aria-checked={entry.checked}
                      disabled={entry.disabled}
                      onClick={() => {
                        close();
                        entry.onSelect?.();
                      }}
                      className="flex min-h-[30px] w-full items-center gap-2 rounded-sm pl-1.5 pr-2.5 text-left hover:bg-wb-selected disabled:cursor-default disabled:hover:bg-transparent"
                    >
                      <span aria-hidden="true" className="flex w-4 text-brand-accent">
                        {entry.checked && <Check size={14} strokeWidth={3} />}
                      </span>
                      <span className={clsx("flex-1", entry.disabled && "text-text-secondary")}>{entry.label}</span>
                      {entry.shortcut && <span className="font-mono text-xs text-text-secondary">{entry.shortcut}</span>}
                    </button>
                  ),
                )}
              </div>
            )}
          </div>
        );
      })}
      {trailing && <span className="ml-auto truncate px-1.5">{trailing}</span>}
    </div>
  );
}
