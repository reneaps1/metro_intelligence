import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./layouts/AppShell";
import { LoginPage } from "./features/auth/LoginPage";
import { CatalogListPage } from "./features/catalog/CatalogListPage";
import { PartDetailPage } from "./features/catalog/PartDetailPage";
import { MeasurementsListPage } from "./features/measurements/MeasurementsListPage";
import { CharacteristicTrendPage } from "./features/measurements/CharacteristicTrendPage";
import { RiskPage } from "./features/risk/RiskPage";
import { DashboardPage } from "./features/dashboards/DashboardPage";
import { useAuth } from "./lib/auth/AuthProvider";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

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
        <Route path="/catalog" element={<CatalogListPage />} />
        <Route path="/catalog/:partId" element={<PartDetailPage />} />
        <Route path="/measurements" element={<MeasurementsListPage />} />
        <Route path="/measurements/:characteristicId" element={<CharacteristicTrendPage />} />
        <Route path="/risk" element={<RiskPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
