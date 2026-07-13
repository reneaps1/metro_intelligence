import { Link } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { Card } from "../../components/ui/Card";

// F5.4 (MI-33): shown by RequireRole when a signed-in user's role isn't
// allowed on a route -- deliberately no mention of which role would work,
// since that's information disclosure about the RBAC matrix to a user who
// isn't authorized to see it.
export function ForbiddenPage() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <Card raised className="w-full max-w-md text-center">
        <ShieldAlert className="mx-auto mb-3 text-status-nok" size={32} aria-hidden="true" />
        <h1 className="text-lg font-semibold text-text-primary">You don't have access to this page</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Your account doesn't have permission to view this section. Contact an administrator if you believe this
          is a mistake.
        </p>
        <Link
          to="/dashboard"
          className="mt-4 inline-flex min-h-[44px] items-center justify-center rounded bg-brand-primary px-4 text-sm font-medium text-text-on-brand transition-colors duration-150 hover:bg-brand-primary-hover"
        >
          Back to dashboard
        </Link>
      </Card>
    </div>
  );
}
