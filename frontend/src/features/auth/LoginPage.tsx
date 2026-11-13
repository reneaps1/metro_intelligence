import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/auth/AuthProvider";
import { ApiError } from "../../lib/api";
import { Card } from "../../components/ui/Card";
import { PartViewLogo } from "../../components/brand/PartViewLogo";
import { Button } from "../../components/ui/Button";

const EMAIL_SHAPE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validateEmail(value: string): string | null {
  if (!value.trim()) return "Falta el correo.";
  if (!EMAIL_SHAPE.test(value)) return "El correo no tiene un formato válido.";
  return null;
}

function validatePassword(value: string): string | null {
  if (!value) return "Falta la contraseña.";
  return null;
}

interface LocationState {
  from?: string;
}

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [touched, setTouched] = useState<{ email?: boolean; password?: boolean }>({});
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const emailError = touched.email ? validateEmail(email) : null;
  const passwordError = touched.password ? validatePassword(password) : null;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setTouched({ email: true, password: true });
    if (validateEmail(email) || validatePassword(password)) return;

    setSubmitting(true);
    setFormError(null);
    try {
      await login(email, password);
      const redirectTo = (location.state as LocationState | null)?.from ?? "/dashboard";
      navigate(redirectTo, { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) setFormError("Correo o contraseña incorrectos.");
      else if (err instanceof ApiError && err.status === 429) setFormError("Demasiados intentos. Esperar un minuto y reintentar.");
      else setFormError(err instanceof ApiError ? err.message : "No se pudo conectar con el servidor. Reintentar en unos segundos.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-surface-app p-6">
      <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
        Powered by OnKaizen
      </span>
      <Card raised className="w-full max-w-md">
        <div className="mb-6 flex justify-center">
          <h1 className="flex justify-center text-2xl">
            <PartViewLogo size={36} />
          </h1>
        </div>
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label htmlFor="email" className="mb-1 block text-sm font-medium text-text-primary">
              Correo
            </label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onBlur={() => setTouched((t) => ({ ...t, email: true }))}
              aria-invalid={emailError ? true : undefined}
              aria-describedby={emailError ? "email-error" : undefined}
              className="min-h-[44px] w-full rounded border border-border bg-surface px-3 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-status-info"
            />
            {emailError && (
              <p id="email-error" role="alert" className="mt-1 text-xs text-status-nok">
                {emailError}
              </p>
            )}
          </div>
          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium text-text-primary">
              Contraseña
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onBlur={() => setTouched((t) => ({ ...t, password: true }))}
              aria-invalid={passwordError ? true : undefined}
              aria-describedby={passwordError ? "password-error" : undefined}
              className="min-h-[44px] w-full rounded border border-border bg-surface px-3 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-status-info"
            />
            {passwordError && (
              <p id="password-error" role="alert" className="mt-1 text-xs text-status-nok">
                {passwordError}
              </p>
            )}
          </div>
          {formError && (
            <p role="alert" className="rounded bg-status-nok-bg px-3 py-2 text-sm text-status-nok">
              {formError}
            </p>
          )}
          <Button type="submit" className="w-full" loading={submitting} disabled={submitting}>
            {submitting ? "Entrando…" : "Entrar"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
