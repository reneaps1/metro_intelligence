import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Info, X } from "lucide-react";
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

// Optional contact address for the expired-access notice, fixed at build time.
const CONTACT_EMAIL: string | undefined = import.meta.env.VITE_CONTACT_EMAIL || undefined;

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
  // Shown after a rejected sign-in: demo credentials are rotated, so an
  // access that used to work may simply have expired.
  const [expiredNotice, setExpiredNotice] = useState(false);

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
      const redirectTo = (location.state as LocationState | null)?.from ?? "/process";
      navigate(redirectTo, { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setFormError("Correo o contraseña incorrectos.");
        setExpiredNotice(true);
      } else if (err instanceof ApiError && err.status === 429) setFormError("Demasiados intentos. Esperar un minuto y reintentar.");
      else setFormError(err instanceof ApiError ? err.message : "No se pudo conectar con el servidor. Reintentar en unos segundos.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-surface-app p-6">
      {expiredNotice && (
        <div
          role="status"
          aria-live="polite"
          className="fixed inset-x-4 top-4 z-toast mx-auto flex max-w-md items-start gap-3 rounded border border-border bg-surface-raised p-4 shadow-md sm:inset-x-auto sm:right-4 sm:mx-0"
        >
          <Info size={20} className="mt-0.5 shrink-0 text-status-info" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-text-primary">¿Tu acceso demo dejó de funcionar?</p>
            <p className="mt-1 text-sm text-text-secondary">
              Los accesos demo anteriores ya expiraron. Para solicitar uno nuevo, ponte en contacto con nosotros
              {CONTACT_EMAIL ? (
                <>
                  {" en "}
                  <a href={`mailto:${CONTACT_EMAIL}`} className="font-medium text-brand-primary hover:underline">
                    {CONTACT_EMAIL}
                  </a>
                </>
              ) : null}
              .
            </p>
          </div>
          <button
            type="button"
            onClick={() => setExpiredNotice(false)}
            aria-label="Cerrar aviso"
            className="-m-2 flex h-11 w-11 shrink-0 items-center justify-center rounded text-text-secondary hover:bg-surface-app hover:text-text-primary"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>
      )}
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
