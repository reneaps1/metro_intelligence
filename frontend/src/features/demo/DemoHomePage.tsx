import { Link, useNavigate } from "react-router-dom";
import clsx from "clsx";
import { useAsync } from "../../lib/catalog/hooks";
import { useDemoSession } from "../../lib/demo/DemoSessionProvider";
import { ORIGIN_INFO, type DataOrigin } from "../../lib/demo/origin";
import { DEMO_STEPS, LINE_PANEL_PATH, stepPath } from "../../lib/demo/steps";
import { fetchDatasets, fetchOverview } from "../../lib/quality-analytics/api";
import { formatPct } from "../../lib/quality-analytics/filters";
import { useDataset } from "../../lib/quality-analytics/useDataset";

// Demo home as a dashboard of the selected part (OnKaizen enterprise style,
// 2026-11-12): a one-line header, a strip of figures that each open the step
// that explains them, and the walkthrough as a dense table. No cards, notes
// or decorative icons; what each data origin means lives in a tooltip.

const n = (v: number) => v.toLocaleString("es-MX");

function day(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" });
}

function Origins({ origins }: { origins: DataOrigin[] }) {
  if (!origins.length) return <span className="text-text-secondary">—</span>;
  return (
    <span className="text-text-secondary">
      {origins.map((o, i) => (
        <span key={o}>
          {i > 0 && " · "}
          <abbr title={ORIGIN_INFO[o].description} className="cursor-help no-underline">
            {ORIGIN_INFO[o].label}
          </abbr>
        </span>
      ))}
    </span>
  );
}

interface Figure {
  label: string;
  value: string;
  detail: string;
  to: string;
  hint: string;
}

const cell = "border-r border-border px-3";

export function DemoHomePage() {
  const navigate = useNavigate();
  const { qualityFilters: f } = useDemoSession();
  const firstStep = DEMO_STEPS[0];
  const step = (id: string) => stepPath(DEMO_STEPS.find((s) => s.id === id) ?? firstStep);

  const datasets = useAsync(fetchDatasets, []);
  const part = useDataset(f.datasetId, datasets.data?.items ?? null);
  const ds = part.dataset;
  const overview = useAsync(
    () => (ds ? fetchOverview(f, ds.utc_offset_minutes ?? 0) : Promise.resolve(null)),
    [ds?.id, JSON.stringify({ ...f, detailVariable: "", groupBy: "" })],
  );
  const s = overview.data?.summary ?? null;
  const loading = datasets.loading || part.loading || overview.loading || (Boolean(ds) && !s && !overview.error);
  const error = datasets.error ?? part.error ?? overview.error;
  const period = s ? `${day(s.period_start)} – ${day(s.period_end)}` : "";
  const varName = (key: string) => ds?.variables.find((v) => v.key === key)?.name ?? key;
  const worst = s?.worst_cavity ?? null;
  const topVar = s?.top_variables[0] ?? null;

  const figures: Figure[] = [
    {
      label: "Piezas medidas",
      value: s ? n(s.pieces) : "—",
      detail: s ? `${n(s.measurements)} mediciones` : "",
      to: step("quality"),
      hint: "Abrir Diagnóstico de calidad",
    },
    {
      label: "Piezas NOK",
      value: s ? formatPct(s.nok_rate, 1) : "—",
      detail: s ? `${n(s.nok_pieces)} de ${n(s.pieces)}` : "",
      to: step("quality"),
      hint: s?.nok_definition ?? "Abrir Diagnóstico de calidad",
    },
    {
      label: "Nido crítico",
      value: worst ? `Nido ${worst.cavity}` : "—",
      detail: worst ? `${formatPct(worst.rate, 1)} NOK · ${n(worst.pieces)} piezas` : "",
      to: step("quality"),
      hint: "Abrir la tasa de NOK por nido",
    },
    {
      label: "Variable con más NOK",
      value: topVar ? varName(topVar) : "—",
      detail: s ? `${n(s.variables_with_tolerance)} variables con tolerancia` : "",
      to: step("dimensional"),
      hint: "Abrir Exploración dimensional",
    },
  ];

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-semibold text-text-primary">Demo industrial</h1>
          <p className="truncate text-sm text-text-secondary">
            {ds?.name ?? "Pieza"}
            {period && ` · ${period}`}
          </p>
        </div>
        <button
          type="button"
          onClick={() => navigate(LINE_PANEL_PATH)}
          className="min-h-[34px] rounded-[3px] border border-border bg-surface px-3 text-sm font-medium text-text-primary hover:bg-wb-pane-header"
        >
          Panel en línea
        </button>
        <button
          type="button"
          onClick={() => navigate(stepPath(firstStep))}
          className="min-h-[34px] rounded-[3px] bg-brand-primary px-3 text-sm font-semibold text-text-on-brand hover:bg-brand-primary-hover"
        >
          Iniciar recorrido
        </button>
      </header>

      <section aria-label="Indicadores de la pieza" className="rounded-[4px] border border-border bg-surface">
        {error ? (
          <div role="alert" className="flex flex-wrap items-center gap-3 px-4 py-3 text-sm">
            <span className="text-status-nok">No se pudieron cargar los indicadores: {error}</span>
            <button
              type="button"
              onClick={() => {
                datasets.refetch();
                overview.refetch();
              }}
              className="min-h-[30px] rounded-[3px] border border-border px-3 hover:bg-wb-pane-header"
            >
              Reintentar
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-4" aria-busy={loading}>
            {figures.map((fig, i) => (
              <Link
                key={fig.label}
                to={fig.to}
                title={fig.hint}
                className={clsx(
                  "block min-w-0 px-4 py-3 hover:bg-wb-pane-header",
                  i % 2 === 1 && "border-l border-border",
                  i >= 2 && "border-t border-border lg:border-t-0",
                  i === 2 && "lg:border-l",
                )}
              >
                <span className="block text-xs text-text-secondary">{fig.label}</span>
                <span className="block truncate text-2xl font-bold tabular-nums text-text-primary">
                  {loading ? "…" : fig.value}
                </span>
                <span className="block min-h-[16px] truncate font-mono text-xs text-text-secondary">
                  {loading ? "" : fig.detail}
                </span>
              </Link>
            ))}
          </div>
        )}
      </section>

      <section aria-labelledby="walkthrough-title" className="overflow-hidden rounded-[4px] border border-border bg-surface">
        <h2
          id="walkthrough-title"
          className="border-b border-border bg-wb-pane-header px-3 py-1.5 text-sm font-semibold text-text-primary"
        >
          Recorrido
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-text-secondary">
                <th scope="col" className={clsx(cell, "w-12 py-1 text-right font-medium")}>
                  Paso
                </th>
                <th scope="col" className={clsx(cell, "py-1 font-medium")}>
                  Vista
                </th>
                <th scope="col" className={clsx(cell, "py-1 font-medium")}>
                  Qué muestra
                </th>
                <th scope="col" className="px-3 py-1 font-medium">
                  Datos
                </th>
              </tr>
            </thead>
            <tbody>
              {DEMO_STEPS.map((st, i) => (
                <tr key={st.id} className={clsx("h-7 border-b border-border", i % 2 === 1 && "bg-surface-app/40")}>
                  <td className={clsx(cell, "text-right font-mono text-text-secondary")}>{st.number}</td>
                  <td className={clsx(cell, "whitespace-nowrap")}>
                    <Link to={stepPath(st)} className="font-medium text-brand-primary hover:underline">
                      {st.title}
                    </Link>
                  </td>
                  <td className={clsx(cell, "text-text-primary")}>{st.summary}</td>
                  <td className="whitespace-nowrap px-3">
                    <Origins origins={st.origins} />
                  </td>
                </tr>
              ))}
              <tr className={clsx("h-7", DEMO_STEPS.length % 2 === 1 && "bg-surface-app/40")}>
                <td className={clsx(cell, "text-right font-mono text-text-secondary")}>—</td>
                <td className={clsx(cell, "whitespace-nowrap")}>
                  <Link to={LINE_PANEL_PATH} className="font-medium text-brand-primary hover:underline">
                    Panel de calidad en línea
                  </Link>
                </td>
                <td className={clsx(cell, "text-text-primary")}>
                  Repetición pieza por pieza con paros, atención y reconocimiento.
                </td>
                <td className="whitespace-nowrap px-3">
                  <Origins origins={[]} />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
