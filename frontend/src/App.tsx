import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./layouts/AppShell";
import { LoginPage } from "./features/auth/LoginPage";
import { ImportPage } from "./features/imports/ImportPage";
import { CatalogListPage } from "./features/catalog/CatalogListPage";
import { PartDetailPage } from "./features/catalog/PartDetailPage";
import { MeasurementsListPage } from "./features/measurements/MeasurementsListPage";
import { CharacteristicTrendPage } from "./features/measurements/CharacteristicTrendPage";
import { LiveMonitorPage } from "./features/live-monitor/LiveMonitorPage";
import { RiskPage } from "./features/risk/RiskPage";
import { DashboardPage } from "./features/dashboards/DashboardPage";
import { RecommendationsInboxPage } from "./features/recommendations/RecommendationsInboxPage";
import { RequireAuth } from "./lib/auth/guards";

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
        <Route path="/risk" element={<RiskPage />} />
        <Route path="/recommendations" element={<RecommendationsInboxPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
