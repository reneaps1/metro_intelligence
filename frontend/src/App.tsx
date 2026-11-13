import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./layouts/AppShell";
import { WorkbenchLayout } from "./layouts/WorkbenchLayout";
import { LoginPage } from "./features/auth/LoginPage";
import { ImportPage } from "./features/imports/ImportPage";
import { CatalogListPage } from "./features/catalog/CatalogListPage";
import { PartDetailPage } from "./features/catalog/PartDetailPage";
import { RequireAuth } from "./lib/auth/guards";
import { RequireEdition } from "./lib/edition/EditionProvider";
import { DemoShell } from "./features/demo/DemoShell";
import { DemoHomePage } from "./features/demo/DemoHomePage";
import { DemoStepPage } from "./features/demo/DemoStepPage";
import { DEMO_BASE_PATH, LINE_PANEL_PATH } from "./lib/demo/steps";
import { LinePanelPage } from "./features/line-panel/LinePanelPage";
import { ProcessOverviewPage } from "./features/process/ProcessOverviewPage";
import { OperationDetailPage } from "./features/process/OperationDetailPage";
import { PieceTracePage } from "./features/process/PieceTracePage";

// ADR-004: the platform runs on the real line data. Screens that only showed
// generated demo data (dashboard, measurements, live monitor, risk,
// recommendations) are not routed until they read the real API; their old
// paths land on the process view.
export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Navigate to="/process" replace />} />
        <Route path="/process" element={<ProcessOverviewPage />} />
        <Route path="/process/operations/:operationId" element={<OperationDetailPage />} />
        <Route path="/process/pieces" element={<PieceTracePage />} />
        <Route path="/process/pieces/:serial" element={<PieceTracePage />} />
        <Route path="/imports" element={<ImportPage />} />
        <Route path="/catalog" element={<CatalogListPage />} />
        <Route path="/catalog/:partId" element={<PartDetailPage />} />
      </Route>
      <Route
        element={
          <RequireAuth>
            <WorkbenchLayout />
          </RequireAuth>
        }
      >
        <Route
          path={LINE_PANEL_PATH}
          element={
            <RequireEdition edition="industrial">
              <LinePanelPage />
            </RequireEdition>
          }
        />
        <Route
          path={DEMO_BASE_PATH}
          element={
            <RequireEdition edition="industrial">
              <DemoShell />
            </RequireEdition>
          }
        >
          <Route index element={<DemoHomePage />} />
          <Route path=":stepId" element={<DemoStepPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/process" replace />} />
    </Routes>
  );
}
