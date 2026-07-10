import { useNavigate } from "react-router-dom";
import { DEMO_USERS } from "../../lib/mock/fixtures";
import { useAuth } from "../../lib/auth/AuthProvider";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";

const ROLE_DESCRIPTIONS: Record<string, string> = {
  viewer: "Read-only dashboards and reports.",
  metrologist: "Imports measurement files and reviews evidence.",
  quality_engineer: "Reviews risk and accepts/rejects recommendations.",
  admin: "Administers master data, users, and configuration.",
  auditor: "Read-only access to the traceability record.",
};

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = (userId: string) => {
    login(userId);
    navigate("/dashboard");
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-app p-6">
      <Card raised className="w-full max-w-md">
        <div className="mb-6 text-center">
          <h1 className="text-xl font-semibold text-text-primary">Metro Intelligence</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Demo login — pick a role to explore the golden path (no real credentials yet).
          </p>
        </div>
        <div className="space-y-2">
          {DEMO_USERS.map((user) => (
            <button
              key={user.id}
              type="button"
              onClick={() => handleLogin(user.id)}
              className="flex min-h-[44px] w-full items-center justify-between rounded border border-border px-4 py-2 text-left transition-colors hover:bg-surface-app"
            >
              <span>
                <span className="block text-sm font-medium text-text-primary">{user.displayName}</span>
                <span className="block text-xs text-text-secondary">{ROLE_DESCRIPTIONS[user.role]}</span>
              </span>
              <span className="rounded bg-status-info-bg px-2 py-0.5 text-xs font-medium capitalize text-status-info">
                {user.role.replace("_", " ")}
              </span>
            </button>
          ))}
        </div>
        <Button variant="ghost" className="mt-4 w-full" onClick={() => handleLogin(DEMO_USERS[1].id)}>
          Skip — continue as Quality Engineer
        </Button>
      </Card>
    </div>
  );
}
