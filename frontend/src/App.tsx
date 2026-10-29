import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./layouts/AppShell";
import { WorkbenchLayout } from "./layouts/WorkbenchLayout";
import { LoginPage } from "./features/auth/LoginPage";
import { ImportPage } from "./features/imports/ImportPage";
import { CatalogListPage } from "./features/catalog/CatalogListPage";
import { PartDetailPage } from "./features/catalog/PartDetailPage";
import { MeasurementsListPage } from "./features/measurements/MeasurementsListPage";
import { CharacteristicTrendPage } from "./features/measurements/CharacteristicTrendPage";
import { LiveMonitorPage } from "./features/live-monitor/LiveMonitorPage";
import { LiveMonitorDetailPage } from "./features/live-monitor/LiveMonitorDetailPage";
import { RiskPage } from "./features/risk/RiskPage";
import { DashboardPage } from "./features/dashboards/DashboardPage";
import { RecommendationsInboxPage } from "./features/recommendations/RecommendationsInboxPage";
import { RequireAuth } from "./lib/auth/guards";
import { RequireEdition } from "./lib/edition/EditionProvider";
import { DemoShell } from "./features/demo/DemoShell";
import { DemoHomePage } from "./features/demo/DemoHomePage";
import { DemoStepPage } from "./features/demo/DemoStepPage";
import { DEMO_BASE_PATH, LINE_PANEL_PATH } from "./lib/demo/steps";
import { LinePanelPage } from "./features/line-panel/LinePanelPage";

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
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/imports" element={<ImportPage />} />
        <Route path="/catalog" element={<CatalogListPage />} />
        <Route path="/catalog/:partId" element={<PartDetailPage />} />
        <Route path="/measurements" element={<MeasurementsListPage />} />
        <Route path="/measurements/:characteristicId" element={<CharacteristicTrendPage />} />
        <Route path="/live-monitor" element={<LiveMonitorPage />} />
        <Route path="/live-monitor/:characteristicId" element={<LiveMonitorDetailPage />} />
        <Route path="/risk" element={<RiskPage />} />
        <Route path="/recommendations" element={<RecommendationsInboxPage />} />
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
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
