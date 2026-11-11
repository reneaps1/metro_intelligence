// Demo branding: marks every screen as an OnKaizen demonstration so the
// system can be shown in full while discouraging redistribution.
//
// Variant resolution: `?marca=a|b|c|off` in the URL (remembered in this
// browser, for previewing the proposals) > VITE_DEMO_BRAND (build-time) > "b".

export type BrandVariant = "a" | "b" | "c" | "off";

export const BRAND_VARIANTS: readonly BrandVariant[] = ["a", "b", "c"];
export const BRAND_STORAGE_KEY = "mi-demo-brand";
const QUERY_KEY = "marca";

export const BRAND_NAMES: Record<Exclude<BrandVariant, "off">, string> = {
  a: "Sello ejecutivo",
  b: "Marca de agua personal",
  c: "Edición evaluación",
};

export const OWNER = "OnKaizen";
export const LEGAL_NOTICE =
  "Demostración confidencial · Propiedad de OnKaizen · Prohibida su copia o distribución sin autorización escrita";

function isVariant(value: string | null | undefined): value is BrandVariant {
  return value === "a" || value === "b" || value === "c" || value === "off";
}

function readStorage(): string | null {
  try {
    return window.localStorage.getItem(BRAND_STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeStorage(value: BrandVariant): void {
  try {
    window.localStorage.setItem(BRAND_STORAGE_KEY, value);
  } catch {
    // Private mode / blocked storage: the variant just isn't remembered.
  }
}

/** Default from the build; falls back to "b" (the most protective that stays professional). */
export function buildVariant(env: string | undefined = import.meta.env.VITE_DEMO_BRAND): BrandVariant {
  const v = env?.trim().toLowerCase();
  return isVariant(v) ? v : "b";
}

/** True when the viewer is previewing proposals (chose one with ?marca=). */
export function isPreviewing(): boolean {
  return isVariant(readStorage());
}

export function resolveVariant(search: string = window.location.search): BrandVariant {
  const fromQuery = new URLSearchParams(search).get(QUERY_KEY)?.toLowerCase() ?? null;
  if (isVariant(fromQuery)) {
    writeStorage(fromQuery);
    return fromQuery;
  }
  const stored = readStorage();
  return isVariant(stored) ? stored : buildVariant();
}

export function chooseVariant(value: BrandVariant): void {
  writeStorage(value);
}

/** Tiled diagonal watermark as an SVG data URL (gray works on light and dark themes). */
export function watermarkUrl(lines: string[], opacity: number): string {
  const text = lines
    .map(
      (line, i) =>
        `<text x="0" y="${i * 22}" font-family="Inter, system-ui, sans-serif" font-size="${i === 0 ? 18 : 12}" font-weight="${i === 0 ? 700 : 500}" fill="rgb(128,128,128)" fill-opacity="${opacity}">${escapeXml(line)}</text>`,
    )
    .join("");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="420" height="260"><g transform="translate(40 190) rotate(-24)">${text}</g></svg>`;
  return `url("data:image/svg+xml,${encodeURIComponent(svg)}")`;
}

function escapeXml(value: string): string {
  return value.replace(/[<>&"']/g, (c) => `&#${c.charCodeAt(0)};`);
}
