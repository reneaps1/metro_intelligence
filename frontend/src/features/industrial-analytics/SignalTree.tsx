import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, GripVertical, Plus, Search } from "lucide-react";
import clsx from "clsx";
import type { SignalInfo, SignalTreeNode } from "../../lib/industrial-signals/types";

// IQ-F3: plant -> area -> line -> machine -> group -> channel tree. Leaves are
// draggable onto the chart area; the "Agregar" button is the accessible
// fallback for keyboards, touch screens and browsers where DnD misbehaves.
export const SIGNAL_DRAG_MIME = "application/x-mi-signal";

const VALUE_TYPE_LABEL: Record<SignalInfo["value_type"], string> = {
  analog: "analógica",
  digital: "digital",
  discrete: "discreta",
  counter: "contador",
};

export function rateLabel(signal: SignalInfo): string {
  return signal.rate_hz ? `${signal.rate_hz} Hz` : "por ciclo";
}

function matches(node: SignalTreeNode, query: string): boolean {
  if (node.node_type === "signal" && node.signal) {
    const s = node.signal;
    return [s.name, s.key, s.unit, s.machine_code].some((v) => v.toLowerCase().includes(query));
  }
  return node.children.some((child) => matches(child, query));
}

// Everything down to the machines is open; only the first machine's signal
// groups start expanded so the presenter sees channels on first click.
function defaultExpanded(root: SignalTreeNode): Set<string> {
  const ids = new Set<string>();
  let firstMachine = true;
  const walk = (node: SignalTreeNode) => {
    if (node.node_type === "signal" || node.node_type === "group") return;
    ids.add(node.id);
    if (node.node_type === "machine") {
      if (firstMachine) node.children.forEach((group) => ids.add(group.id));
      firstMachine = false;
      return;
    }
    node.children.forEach(walk);
  };
  walk(root);
  return ids;
}

interface SignalTreeProps {
  root: SignalTreeNode;
  activeIds: Set<string>;
  full: boolean;
  onAdd: (signal: SignalInfo) => void;
}

export function SignalTree({ root, activeIds, full, onAdd }: SignalTreeProps) {
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(() => defaultExpanded(root));
  const q = query.trim().toLowerCase();

  const toggle = (id: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const visibleRoot = useMemo(() => (q && !matches(root, q) ? null : root), [root, q]);

  function renderNode(node: SignalTreeNode, depth: number) {
    if (q && !matches(node, q)) return null;

    if (node.node_type === "signal" && node.signal) {
      const signal = node.signal;
      const active = activeIds.has(signal.signal_id);
      return (
        <li
          key={node.id}
          draggable={!active}
          onDragStart={(e) => {
            e.dataTransfer.setData(SIGNAL_DRAG_MIME, signal.signal_id);
            e.dataTransfer.setData("text/plain", signal.signal_id);
            e.dataTransfer.effectAllowed = "copy";
          }}
          className={clsx(
            "group flex items-center gap-1 rounded px-1 py-1 text-xs",
            active ? "opacity-60" : "cursor-grab hover:bg-surface-app",
          )}
          style={{ paddingLeft: depth * 12 }}
          data-signal-id={signal.signal_id}
        >
          <GripVertical size={12} className="shrink-0 text-text-secondary" aria-hidden="true" />
          <span className="min-w-0 flex-1">
            <span className="block truncate font-medium text-text-primary" title={signal.description}>
              {signal.name}
            </span>
            <span className="block truncate text-text-secondary">
              {signal.unit} · {rateLabel(signal)} · {VALUE_TYPE_LABEL[signal.value_type]}
              {signal.causal_imposed && <span className="ml-1 font-semibold text-status-warning">· Vista B</span>}
              {!signal.informative && <span className="ml-1 italic">· control</span>}
            </span>
          </span>
          <button
            type="button"
            onClick={() => onAdd(signal)}
            disabled={active || full}
            aria-label={`Agregar ${signal.name} ${signal.machine_code}`}
            title={active ? "Ya está en la gráfica" : full ? "Máximo de señales alcanzado" : "Agregar a la gráfica"}
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded text-text-secondary hover:bg-surface hover:text-brand-primary disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Plus size={14} aria-hidden="true" />
          </button>
        </li>
      );
    }

    const open = q.length > 0 || expanded.has(node.id);
    return (
      <li key={node.id}>
        <button
          type="button"
          onClick={() => toggle(node.id)}
          aria-expanded={open}
          className="flex w-full items-center gap-1 rounded px-1 py-1 text-left text-xs font-semibold text-text-primary hover:bg-surface-app"
          style={{ paddingLeft: depth * 12 }}
        >
          {open ? <ChevronDown size={14} aria-hidden="true" /> : <ChevronRight size={14} aria-hidden="true" />}
          {node.name}
        </button>
        {open && <ul>{node.children.map((child) => renderNode(child, depth + 1))}</ul>}
      </li>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <label className="relative mb-2 block">
        <span className="sr-only">Buscar señal</span>
        <Search size={14} className="absolute left-2 top-2.5 text-text-secondary" aria-hidden="true" />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar señal, unidad o máquina"
          className="w-full rounded border border-border bg-surface py-1.5 pl-7 pr-2 text-xs text-text-primary"
        />
      </label>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {visibleRoot ? (
          <ul aria-label="Árbol de señales">{renderNode(visibleRoot, 0)}</ul>
        ) : (
          <p className="text-xs text-text-secondary">Ninguna señal coincide con la búsqueda.</p>
        )}
      </div>
    </div>
  );
}
