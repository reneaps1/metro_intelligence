// Demo branding: marks every screen as an OnKaizen demonstration so the
// system can be shown in full while discouraging redistribution.
//
// The variant is fixed at build time (VITE_DEMO_BRAND, default "b": personal
// watermark). Viewers cannot change or remove it from the browser.

export type BrandVariant = "a" | "b" | "c" | "off";

export const OWNER = "OnKaizen";
export const LEGAL_NOTICE =
  "Demostración confidencial · Propiedad de OnKaizen · Prohibida su copia o distribución sin autorización escrita";

function isVariant(value: string | undefined): value is BrandVariant {
  return value === "a" || value === "b" || value === "c" || value === "off";
}

export function buildVariant(env: string | undefined = import.meta.env.VITE_DEMO_BRAND): BrandVariant {
  const v = env?.trim().toLowerCase();
  return isVariant(v) ? v : "b";
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
