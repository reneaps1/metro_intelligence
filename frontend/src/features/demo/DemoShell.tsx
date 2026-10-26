import { useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { ChevronLeft, ChevronRight, RotateCcw } from "lucide-react";
import clsx from "clsx";
import { Button } from "../../components/ui/Button";
import { useEdition } from "../../lib/edition/EditionProvider";
import { DemoSessionProvider, useDemoSession } from "../../lib/demo/DemoSessionProvider";
import { DEMO_BASE_PATH, DEMO_STEPS, stepPath } from "../../lib/demo/steps";

// IQ-F1: layout for the guided commercial walkthrough -- header, 7-step
// stepper, safe scenario reset and previous/next navigation.
export function DemoShell() {
  return (
    <DemoSessionProvider>
      <DemoLayout />
    </DemoSessionProvider>
  );
}

function DemoLayout() {
  const { clientLabel } = useEdition();
  const { reset, resetCount } = useDemoSession();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [notice, setNotice] = useState<string | null>(null);

  const currentIndex = DEMO_STEPS.findIndex((step) => pathname === stepPath(step));
  const previous = currentIndex > 0 ? stepPath(DEMO_STEPS[currentIndex - 1]) : DEMO_BASE_PATH;
  const next = currentIndex >= 0 && currentIndex < DEMO_STEPS.length - 1 ? DEMO_STEPS[currentIndex + 1] : null;

  function handleReset() {
    reset();
    setNotice("Escenario demo restaurado: operación normal y vistas por defecto. No se modificó ningún dato guardado.");
  }

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-brand-primary">
            Industrial Quality Intelligence
          </p>
          <h1 className="text-xl font-semibold text-text-primary">
            <Link to={DEMO_BASE_PATH} className="hover:underline">
              Analítica dimensional, IA e IIoT
            </Link>
          </h1>
          <p className="text-sm text-text-secondary">
            Cliente: <span className="font-medium text-text-primary">{clientLabel}</span>
          </p>
        </div>
        <Button variant="secondary" onClick={handleReset}>
          <RotateCcw size={16} aria-hidden="true" />
          Restaurar escenario demo
        </Button>
      </header>

      {notice && (
        <p role="status" className="rounded bg-status-info-bg px-3 py-2 text-sm text-status-info">
          {notice}
        </p>
      )}

      <nav aria-label="Pasos de la demo" className="overflow-x-auto">
        <ol className="flex min-w-max gap-1">
          {DEMO_STEPS.map((step) => (
            <li key={step.id} className="min-w-[140px] flex-1">
              <NavLink
                to={stepPath(step)}
                className={({ isActive }) =>
                  clsx(
                    "flex h-full items-center gap-2 rounded border px-3 py-2 text-xs font-medium transition-colors",
                    isActive
                      ? "border-brand-primary bg-brand-primary text-text-on-brand"
                      : "border-border bg-surface text-text-secondary hover:text-text-primary",
                  )
                }
              >
                <span className="font-mono text-sm">{step.number}</span>
                <span>{step.title}</span>
              </NavLink>
            </li>
          ))}
        </ol>
      </nav>

      <div key={resetCount}>
        <Outlet />
      </div>

      {currentIndex >= 0 && (
        <footer className="flex items-center justify-between border-t border-border pt-4">
          <Button variant="ghost" onClick={() => navigate(previous)}>
            <ChevronLeft size={16} aria-hidden="true" />
            Anterior
          </Button>
          {next ? (
            <Button onClick={() => navigate(stepPath(next))}>
              Siguiente: {next.title}
              <ChevronRight size={16} aria-hidden="true" />
            </Button>
          ) : (
            <Button variant="secondary" onClick={() => navigate(DEMO_BASE_PATH)}>
              Volver al inicio de la demo
            </Button>
          )}
        </footer>
      )}
    </div>
  );
}
