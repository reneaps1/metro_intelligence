import { useCallback, useEffect, useRef, useState } from "react";
import { Outlet, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../../lib/auth/AuthProvider";
import { useEdition } from "../../lib/edition/EditionProvider";
import { AI_VIEW_PARAM, AI_VIEWS, parseAiView } from "../../lib/demo/aiViews";
import { DemoSessionProvider, useDemoSession } from "../../lib/demo/DemoSessionProvider";
import { useVisiblePanes } from "../../lib/demo/panes";
import { stepOrigins } from "../../lib/demo/stepOrigins";
import { DEMO_BASE_PATH, DEMO_STEPS, LINE_PANEL_PATH, stepPath } from "../../lib/demo/steps";
import { useTheme } from "../../lib/theme/ThemeProvider";
import { Inspector, type InspectorSection } from "./workbench/Inspector";
import { MenuBar, type Menu } from "./workbench/MenuBar";
import { ProjectTree } from "./workbench/ProjectTree";
import { Toolbar } from "./workbench/Toolbar";
import "./workbench/workbench.css";

// Demo workbench (design-system.md §4.1, decisions.md 2026-10-28): menu bar,
// toolbar, project tree, document, inspector and status bar. Every fact lives
// in one place -- location in the tree and the toolbar path, the walkthrough
// position in the toolbar, provenance in the step header and the inspector,
// activity in the status bar. Since 2026-11-12 the demo covers piece
// characteristics only, so the simulated process scenario and its alarms are
// no longer offered here (DemoSessionProvider still holds that state).
export function DemoShell() {
  return (
    <DemoSessionProvider>
      <DemoLayout />
    </DemoSessionProvider>
  );
}

function isTyping(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el) return false;
  return el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName);
}

function DemoLayout() {
  const { clientLabel, edition } = useEdition();
  const { user, logout } = useAuth();
  const { resolvedTheme, setPreference } = useTheme();
  const session = useDemoSession();
  const { qualityFilters, resetCount } = session;
  const { pathname } = useLocation();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { visible, toggle } = useVisiblePanes();
  const [lastAction, setLastAction] = useState("Abrir vista: inicio de la demo");
  const documentRef = useRef<HTMLElement>(null);

  const currentIndex = DEMO_STEPS.findIndex((step) => pathname === stepPath(step));
  const currentStep = currentIndex >= 0 ? DEMO_STEPS[currentIndex] : null;
  const isDark = resolvedTheme === "dark";
  const aiView = currentStep?.id === "ai" ? AI_VIEWS.find((v) => v.id === parseAiView(searchParams.get(AI_VIEW_PARAM))) : null;

  const loggedPath = useRef<string | null>(null);
  useEffect(() => {
    if (loggedPath.current === pathname) return;
    loggedPath.current = pathname;
    setLastAction(currentStep ? `Abrir vista: ${currentStep.number} ${currentStep.title}` : "Abrir vista: inicio de la demo");
    if (documentRef.current) documentRef.current.scrollTop = 0;
  }, [pathname, currentStep]);

  const goPrev = useCallback(() => {
    if (currentIndex > 0) navigate(stepPath(DEMO_STEPS[currentIndex - 1]));
    else if (currentIndex === 0) navigate(DEMO_BASE_PATH);
  }, [currentIndex, navigate]);
  const goNext = useCallback(() => {
    const next = currentIndex + 1;
    navigate(next < DEMO_STEPS.length ? stepPath(DEMO_STEPS[next]) : DEMO_BASE_PATH);
  }, [currentIndex, navigate]);

  // Presentation clickers send Re Pág / Av Pág: they walk the demo (except while typing).
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.altKey || event.ctrlKey || event.metaKey || isTyping(event.target)) return;
      if (event.key === "PageDown") {
        event.preventDefault();
        goNext();
      } else if (event.key === "PageUp") {
        event.preventDefault();
        goPrev();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [goNext, goPrev]);

  function toggleTheme() {
    setPreference(isDark ? "light" : "dark");
    setLastAction(`Tema: ${isDark ? "claro" : "oscuro"}`);
  }

  const menus: Menu[] = [
    {
      id: "archivo",
      label: "Archivo",
      entries: [
        { label: "Volver a la plataforma", onSelect: () => navigate("/dashboard") },
        { label: "Cerrar sesión", onSelect: logout },
      ],
    },
    {
      id: "ver",
      label: "Ver",
      entries: [
        { label: "Árbol del proyecto", checked: visible.tree, onSelect: () => toggle("tree") },
        { label: "Inspector", checked: visible.inspector, onSelect: () => toggle("inspector") },
        { label: "Tema oscuro", checked: isDark, onSelect: toggleTheme },
        { separator: true },
        { label: "Panel de calidad en línea", onSelect: () => navigate(LINE_PANEL_PATH) },
      ],
    },
    {
      id: "ayuda",
      label: "Ayuda",
      entries: [
        { label: "Cómo leer la procedencia", onSelect: () => navigate(DEMO_BASE_PATH) },
        { label: "Paso anterior / siguiente", shortcut: "Re Pág / Av Pág", disabled: true },
      ],
    },
  ];

  const aiDatasetId = currentStep?.id === "ai" ? session.aiDatasetId : null;
  const origins = currentStep ? stepOrigins(currentStep, qualityFilters.datasetId, aiDatasetId) : [];
  const inspectorSections: InspectorSection[] = [
    {
      title: "Vista",
      rows: currentStep
        ? [
            { label: "Paso", value: `${currentStep.number} de ${DEMO_STEPS.length}` },
            { label: "Grupo", value: currentStep.group },
            ...(aiView ? [{ label: "Vista IA", value: aiView.label }] : []),
          ]
        : [{ label: "Paso", value: "Inicio de la demo" }],
    },
  ];
  inspectorSections.push({
    title: "Sesión",
    rows: [
      { label: "Dataset", value: aiDatasetId ?? qualityFilters.datasetId, mono: true },
      { label: "Edición", value: edition },
      { label: "Cliente", value: clientLabel },
      { label: "Usuario", value: user?.displayName ?? "—" },
      { label: "Rol", value: user?.role.replace("_", " ") ?? "—" },
    ],
  });

  const crumbs = currentStep
    ? [currentStep.group, currentStep.short, ...(aiView ? [aiView.label] : [])]
    : ["Inicio de la demo"];
  const prevStep = currentIndex > 0 ? DEMO_STEPS[currentIndex - 1] : null;
  const nextStep = currentIndex + 1 < DEMO_STEPS.length ? DEMO_STEPS[currentIndex + 1] : null;

  return (
    <div className="wb-root flex h-full min-h-0 flex-col bg-surface-app text-text-primary">
      <MenuBar
        menus={menus}
        trailing={`Metro Intelligence · Demo industrial · ${clientLabel}${user ? ` · ${user.displayName}` : ""}`}
      />
      <Toolbar
        treeVisible={visible.tree}
        onToggleTree={() => toggle("tree")}
        inspectorVisible={visible.inspector}
        onToggleInspector={() => toggle("inspector")}
        crumbs={crumbs}
        position={currentStep ? `${currentStep.number} / ${DEMO_STEPS.length}` : "Inicio"}
        atStart={currentIndex < 0}
        prevLabel={prevStep ? `Anterior: ${prevStep.title}` : "Anterior: inicio de la demo"}
        nextLabel={nextStep ? `Siguiente: ${nextStep.title}` : "Volver al inicio de la demo"}
        onPrev={goPrev}
        onNext={goNext}
      />

      <div className="flex min-h-0 flex-1">
        {visible.tree && (
          <ProjectTree isHome={currentIndex < 0} />
        )}
        <main ref={documentRef} className="min-h-0 min-w-0 flex-1 overflow-y-auto p-4">
          <div className="mx-auto max-w-[1440px] space-y-4">
            <div key={resetCount}>
              <Outlet />
            </div>
          </div>
        </main>
        {visible.inspector && <Inspector origins={origins} sections={inspectorSections} />}
      </div>

      <footer className="flex min-h-[26px] flex-none flex-wrap items-center border-t border-border bg-wb-status px-1 text-xs text-wb-status-text">
        <span aria-live="polite" aria-label="Última acción" className="min-w-0 flex-1 truncate px-2">
          {lastAction}
        </span>
        <span className="border-l border-border px-2">Edición {edition}</span>
      </footer>
    </div>
  );
}
