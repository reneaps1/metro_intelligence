import { useAuth } from "../auth/AuthProvider";
import { LEGAL_NOTICE, OWNER, buildVariant, watermarkUrl, type BrandVariant } from "./brand";

// Overlay drawn above every route (login included). Purely visual and
// click-through (pointer-events: none); the variant is fixed at build time.

function Ribbon() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed bottom-0 right-0 z-toast h-28 w-28 overflow-hidden print:fixed"
    >
      <div className="absolute bottom-[26px] right-[-34px] w-[150px] -rotate-45 bg-brand-primary py-1 text-center text-[11px] font-bold uppercase tracking-[0.2em] text-text-on-brand shadow-md">
        Demo
      </div>
    </div>
  );
}

function OwnerPill() {
  return (
    <div className="pointer-events-none fixed bottom-2 left-2 z-toast max-w-[calc(100vw-140px)] truncate rounded-full border border-border bg-surface-raised px-3 py-1 text-[11px] font-medium text-text-secondary shadow-md backdrop-blur">
      <span className="font-bold text-brand-primary">DEMO</span> · PartView · Propiedad de {OWNER} ·
      Confidencial
    </div>
  );
}

function Watermark({ lines, opacity }: { lines: string[]; opacity: number }) {
  return (
    <div
      aria-hidden="true"
      data-testid="demo-watermark"
      className="pointer-events-none fixed inset-0 z-toast print:fixed"
      style={{ backgroundImage: watermarkUrl(lines, opacity), backgroundRepeat: "repeat" }}
    />
  );
}

function LegalStrip() {
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-0 z-toast truncate bg-brand-primary px-4 py-1 pr-32 text-center text-[11px] font-medium text-text-on-brand backdrop-blur">
      <span className="font-bold tracking-[0.2em]">VERSIÓN DEMO</span> — {LEGAL_NOTICE}
    </div>
  );
}

export function DemoBrand({ variant = buildVariant() }: { variant?: BrandVariant }) {
  const { user } = useAuth();
  const date = new Date().toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
  const viewer = user?.email ?? "Acceso restringido";

  return (
    <>
      {variant === "a" && (
        <>
          <Ribbon />
          <OwnerPill />
        </>
      )}
      {variant === "b" && (
        <>
          <Watermark lines={[`${OWNER.toUpperCase()} · DEMO`, `${viewer} · ${date}`, "Confidencial — no distribuir"]} opacity={0.11} />
          <OwnerPill />
        </>
      )}
      {variant === "c" && (
        <>
          <Watermark lines={[`DEMO · ${OWNER.toUpperCase()}`, viewer]} opacity={0.07} />
          <LegalStrip />
          <Ribbon />
        </>
      )}
    </>
  );
}
