# Metro Intelligence — Design System & Brand Manual

Single source of truth for the frontend. **Every screen, component, and chart must use these tokens — no raw hex values in components.** Implemented as CSS variables + Tailwind theme config in `frontend/src/theme/`.

Style direction: **industrial precision** — flat, high-contrast, data-first, generous whitespace, zero decoration that competes with data. No glassmorphism, no gradients on data surfaces, no emoji as icons.

---

## 1. Color system

All colors are defined as **semantic tokens** with a light and dark value. Light and dark are designed together; dark mode uses desaturated/lighter tonal variants, never naive inversion. Contrast verified per WCAG AA (≥4.5:1 body text, ≥3:1 large text/icons) **in both themes**.

### 1.1 Brand

| Token | Light | Dark | Use |
|---|---|---|---|
| `--brand-primary` | `#1E4E8C` (industrial blue) | `#5B8DD9` | Primary actions, active nav, links, focus |
| `--brand-primary-hover` | `#173F73` | `#7AA5E3` | Hover/pressed |
| `--brand-accent` | `#0E7C86` (teal) | `#3FB0BA` | Secondary emphasis, selected filters |

### 1.2 Surfaces & text

| Token | Light | Dark |
|---|---|---|
| `--bg-app` | `#F4F6F8` | `#0F1419` |
| `--bg-surface` (cards, panels) | `#FFFFFF` | `#1A2129` |
| `--bg-surface-raised` (modals, popovers) | `#FFFFFF` + shadow-md | `#232C36` |
| `--bg-sidebar` | `#101828` (always dark) | `#0B1016` |
| `--border-default` | `#D9DEE3` | `#2E3A46` |
| `--text-primary` | `#101828` | `#E6EAEE` |
| `--text-secondary` | `#475467` | `#98A6B3` |
| `--text-disabled` | `#98A2B3` | `#5C6873` |

The sidebar is dark in both themes (stable industrial identity); content area switches.

### 1.3 Semantic status — OK / NOK / process states

**Rule: status is never conveyed by color alone.** Every status pairs color + icon + text label (colorblind safety; WCAG `color-not-only`).

| Token | Light | Dark | Icon (Lucide) | Meaning |
|---|---|---|---|---|
| `--status-ok` | `#1B7F4B` | `#4CC38A` | `check-circle` | OK / in tolerance / stable |
| `--status-nok` | `#C8102E` | `#F0526A` | `x-octagon` | NOK / out of tolerance |
| `--status-warning` | `#B25E09` | `#F5A524` | `alert-triangle` | Near limit / trend risk / attention |
| `--status-info` | `#175CD3` | `#6CA6F5` | `info` | Informational / recommendation pending |
| `--status-neutral` | `#475467` | `#98A6B3` | `minus-circle` | No data / not evaluated |

Backgrounds for status chips: 10–15% tint of the status color (`--status-ok-bg`, etc.), text at full token color.

Risk levels map to: low → `ok`, medium → `warning`, high/critical → `nok` (+ distinct icon `alert-octagon` for critical).

### 1.4 Chart palette (categorical, colorblind-aware)

Order is fixed — series 1 always gets `--chart-1`, etc.:

`--chart-1 #2563EB` · `--chart-2 #0E7C86` · `--chart-3 #9333EA` · `--chart-4 #D97706` · `--chart-5 #DB2777` · `--chart-6 #64748B`

Reserved (never for categorical series): OK/NOK/warning tokens — those appear in charts **only** with their semantic meaning (spec limits, violation points). Gridlines: `--border-default` at 50% opacity. Nominal line: `--text-secondary` dashed. Tolerance limits: `--status-nok` dashed. Control limits (UCL/LCL): `--status-warning` dotted.

## 2. Typography

| Role | Font | Size / weight |
|---|---|---|
| UI + headings | **Inter** (self-hosted — on-premise, no Google CDN at runtime) | Scale: 12 / 14 / 16 / 18 / 24 / 32; headings 600, body 400, labels 500 |
| Data / numbers | **JetBrains Mono** (self-hosted) | Tabular figures for all measurement values, deviations, Cpk, tables |

Body ≥14px (16px preferred), line-height 1.5. Measurement values always monospace with fixed decimals per characteristic unit — no layout shift.

## 3. Iconography policy

- Single icon set: **Lucide** (stroke 2px, outline style). No mixing sets, no filled/outline mixing at the same hierarchy level, **never emoji as icons**.
- Sizes as tokens only: `icon-sm 16px`, `icon-md 20px`, `icon-lg 24px`.
- Icon-only buttons require `aria-label` + tooltip; min touch target 44×44px.
- Domain icon vocabulary (fixed — do not improvise): part `box`, characteristic `crosshair`, measurement run `activity`, machine `cpu`, program `file-code-2`, event `zap`, risk `shield-alert`, recommendation `lightbulb`, decision `check-square`, alert `bell`, report `file-text`, dashboard `layout-dashboard`, settings `settings`, user `user-circle`, audit `scroll-text`.

## 4. Layout & navigation

- **Primary navigation: left sidebar, collapsible** (expanded 264px ↔ collapsed 72px icons+tooltips; state persisted per user). Sections: Dashboard, Parts & Catalog, Measurements, Risk & Recommendations, Alerts, Reports, Administration (RBAC-filtered).
- Active item: left 3px `--brand-primary` bar + tinted background + label weight 500. Icon + label always (labels as tooltips when collapsed).
- **Top bar** (fixed, 56px): breadcrumbs (hierarchies ≥3 levels), global search, theme toggle, notification bell (alert badge), user avatar menu.
- **No floating action buttons for primary flows** (desktop data app — FABs hide actions). Floating elements allowed only for: toasts (bottom-right, auto-dismiss 4s, `aria-live="polite"`), a collapsible filter panel, and "back to top" in long tables.
- Content max-width 1440px centered; 8px spacing grid (4/8/16/24/32/48); z-index scale fixed: base 0 / sticky 10 / dropdown 20 / overlay 40 / modal 50 / toast 100.
- Density: default comfortable; tables offer a compact toggle (user preference).
- Breakpoints 768 / 1024 / 1440 — operational dashboards optimized for desktop + shop-floor 1080p displays; sidebar becomes drawer <1024px.

### 4.1 Engineering workbench layout (industrial demo)

The industrial demo module (`/demo/industrial-quality`, `APP_EDITION=industrial` only) opens full-viewport as a desktop engineering workbench (TIA Portal / iba Analyzer family), following ISA-101 high-performance HMI rules. It replaces the platform sidebar and top bar for that module only; the metrology edition and every other screen keep the layout above. Decision notes: `docs/design/decisions.md` (2026-10-26, 2026-10-28).

**Rule: every fact lives in one place.** Location → project tree + toolbar path. Walkthrough position → toolbar `‹ n / 7 ›` only. Scenario and alarms → toolbar only (steps show a read-only summary). Provenance → step header once, explained in the inspector. Connection and activity → status bar only.

- **Menu bar** (32px, `--wb-chrome`): Archivo · Ver · Escenario · Ayuda. It is the command index (every command reachable from a menu); entries that also exist in the toolbar open the same control, never a copy.
- **Toolbar** (48px, `--wb-pane-header`): tree toggle, path (group › step › view), scenario control (choose + **Aplicar**, two actions; Restaurar), alarm summary (count, priority symbol, Reconocer todas), walkthrough `‹ n / 7 ›` (Re Pág / Av Pág also walk it, for presentation clickers), inspector toggle.
- **Project tree** (left 232px): two levels only (group › numbered step); steps that show the simulated scenario carry its alarm symbol. Assets (INY-01/INY-02) are status rows, not links.
- **Document**: notice line (with Deshacer) + the step page. The step header is the only title of the view.
- **Inspector** (right 288px): technical details of the open view: provenance with its meaning, simulated scenario (description, events, alarms, generator version), session context.
- **Status bar** (26px, `--wb-status`): simulator connection (failure shown in the alarm color), last action, edition.
- **ISA-101 color**: neutral gray surfaces scoped to `.wb-root` (light `#DDE1E5` app; dark graphite `#1B1E22` since IQ-F16 -- darker, but never pure black). Red/amber only for alarms; alarm priority also coded by shape (diamond = P1, triangle = P2) and the symbol blinks only while unacknowledged (stopped by reduced motion). Provenance badges are neutral (icon + label; Experimental dashed). Navigation controls are outlined; action buttons (Aplicar, Reconocer, Deshacer) are solid.
- Simulated alarms come from `lib/demo/alarms.ts` (derived from the scenario, labeled "Simulada"); no engine produces them.
- Below 1024px the tree hides and below 1280px the inspector hides; the toolbar and the menu keep every command reachable.
- Density: desktop pointer targets ≥32px in the menu bar and toolbar (documented exception to the 44px touch target; the workbench is not a touch surface).
### 4.2 Line quality panel (shop-floor display, industrial demo)

`/demo/industrial-quality/panel-linea` opens a full-screen panel for the line, outside the workbench chrome (spec and API contract: `docs/design/line-quality-panel.md`). It is a fixed 1920×1080 canvas scaled to the screen, so a TV at the line shows exactly the composed layout. Three views share one replay: **A Andon** (read from 5–10 m), **B Process map** (line lead / quality technician), **C Guided response** (the alarm becomes the case and its four steps).

- **Color only for action.** Surfaces are the `.wb-root` grays. A single NOK piece is dark neutral (`--lp-piece-nok`); red (`--lp-p1-fill`) appears only on a streak that asked to stop, on a priority-1 band and its KPI. Amber (`--lp-p2-fill`) only for priority 2. Advisories (priority 3) are neutral squares.
- **Priority by shape** (diamond 1, triangle 2, square advisory) and by color; on a solid band the symbol inverts. Symbols blink only while unacknowledged (`.wb-blink`, stopped by reduced motion). Unacknowledged → solid band + escalation countdown; acknowledged → solid, no blink; line stopped → outlined band ("containment").
- **Commands:** R acknowledge, A register action (four numbered options, also one-touch buttons in view C), F full screen. Action buttons are solid only while they apply. Targets ≥52px (touch at the line).
- **Presenter bar** (auto-hides, outside the canvas): views 1/2/3, N/W/S jump to the next real normal / attention / stop moment of the replayed data, pause, speed, theme, back to the workbench.
- New tokens `--lp-*` in `.wb-root` (light/dark): band fills with fixed on-colors, piece strip, bars and the cavity ramp.

### 4.3 Workbench content in the line panel's language (IQ-F16)

The content of every workbench step follows the line quality panel (§4.2) at desktop size, so the demo reads as one product. Styles live in `features/demo/workbench/workbench.css`, scoped to `.wb-root`; shared components (`Card`, `CardHeader`, `Button`) only carry marker classes, so the metrology edition keeps §5 unchanged. Decision note: `decisions.md` (2026-10-28, unified workbench).

- **Cards:** a `CardHeader` as the first child becomes a pane-header band (42px, `--wb-pane-header`, uppercase 12.5px label, letter-spacing 0.06em, context or actions on the right).
- **KPIs:** `components/workbench/Kpi` -- uppercase label, monospaced figure (38px; 30px `sm` inside cards), unit set smaller, footer with the basis. Three columns per row so the figure keeps its size.
- **Color budget:** neutral by default. One muted NOK accent (`--wb-nok`, light `#A64D58` / dark `#D98E97`, about a third of the alarm red's saturation, >= 4.5:1 as text) marks only what has to stand out: NOK pieces and rates, the worst group, outliers and out-of-tolerance points, the busiest heatmap cell. Red/amber (`--lp-p1-fill`, `--lp-p2-fill`) stay for alarms that ask for action. Provenance, source states and banners are neutral.
- **Charts:** `lib/demo/chartTheme.ts` -- bars `--wb-bar`, neutral emphasis `--wb-mark`, comparison or cumulative series as a dashed line in the text color, references dotted and limits dashed with an uppercase label in the right margin ("MEDIA 10.4%"), heatmaps on the neutral `--wb-ramp`. Bar charts have no grid; line charts a faint horizontal one. Exception: IIoT signal pens keep the categorical `--chart-*` palette (each pen is a different signal).
- **Controls:** chips (`wb-chip`, 30px, semibold) and segmented controls (`wb-seg`) show selection with the presenter bar's state (`--wb-selected` tint + `--brand-accent` border/underline); filter labels are uppercase (`wb-label`).
- **Notices:** `components/workbench/Notice` -- neutral surface, icon, 4px left rule; the priority-2 rule only when the user has to act.
- **Shortcuts:** keycaps (`components/workbench/Key`) next to controls that have one (Re Pág / Av Pág in the toolbar at wide widths).

## 5. Components (standard behaviors)

- **Buttons:** one primary per view; destructive = danger color + confirmation dialog; loading = spinner + disabled. Radius 6px everywhere.
- **Tables:** sticky header, sortable (`aria-sort`), monospace numerics right-aligned, status chips (color+icon+text), row hover, virtualized >50 rows, empty/loading/error states mandatory (skeleton, never blank).
- **Forms:** visible labels (never placeholder-only), validation on blur, error text below field, helper text for tolerance/unit inputs, autofocus first invalid field on submit.
- **Modals:** for confirmation and small edits only — never primary navigation; scrim 50% black; Escape + explicit close; focus trapped.
- **Charts:** legend visible and clickable (toggle series), tooltips with exact values on hover, axis units always labeled, `prefers-reduced-motion` respected, table-view alternative for accessibility, skeleton while loading, error state with retry.
- Motion: 150–250ms, ease-out enter / ease-in exit, transform/opacity only; respect reduced motion.

## 6. Chart type standards (SPC / quality)

| Need | Chart | Notes |
|---|---|---|
| Individual measurements over time | **I-MR chart** (line + points) | Nominal, tolerance, control limits as reference lines; violation points marked NOK color + shape (triangle) |
| Subgrouped process control | **X̄-R chart** | Same reference-line conventions |
| Capability snapshot | **Histogram + spec limits** (+ optional curve) | Cp/Cpk displayed as monospace stat tiles beside chart |
| Trend/drift emphasis | Line + regression overlay | Slope shown in tooltip |
| Characteristic comparison | Horizontal bar | Sorted by risk/Cpk; never pie for >5 categories |
| Risk overview per part | Heatmap (characteristics × time) | Sequential single-hue ramp + value in tooltip; legend with thresholds |
| OK/NOK composition | Stacked bar over time | Only 2–3 segments; no donuts on operational screens |
| Executive KPIs | Stat tiles + sparklines | Tile = value (mono, large) + delta arrow + label + sparkline |

Never: 3D charts, dual-axis without explicit labeling, decorative gradients/shadows on data.

## 7. Theming: light & dark mode

- Both themes ship from the first demo screen. Toggle in top bar; default follows OS (`prefers-color-scheme`); choice persisted per user profile.
- Implementation: CSS variables on `:root` / `[data-theme="dark"]`; Tailwind reads variables — components use only semantic tokens.
- Every PR that touches UI is reviewed in both themes (screenshot both in PR description). Charts re-read tokens on theme switch.

## 8. User profile, settings & light personalization

Personalization is deliberately **light** — preferences, never layout anarchy. All stored per user (`user_preference` table / `/api/v1/me/preferences`).

**Profile menu (avatar, top-right):** name, role badge, "My profile", "Preferences", theme quick-toggle, sign out.

**My profile:** display name, avatar initials (no photo upload in MVP), role(s) — read-only, contact, last login (from audit).

**Preferences (user-editable):**
- Theme: light / dark / system.
- Language: es / en (i18n-ready from the start; demo ships es-MX + en).
- Number & date format: decimals shown, date format, timezone display.
- Table density: comfortable / compact.
- Default landing page: operational dashboard / executive dashboard / my alerts.
- Notification preferences: which alert severities appear as toasts vs. bell-only.
- Dashboard: pin/favorite up to N cards; order of pinned cards. (No free-form dashboard builder in MVP.)
- Sidebar collapsed state (auto-persisted).

**Admin-only settings (separate section, RBAC-gated):** organization/site data, users & roles, connectors/data sources, alert thresholds, SPC rule set toggles, retention policies. Never mixed into personal preferences.

## 9. Accessibility baseline (non-negotiable)

WCAG 2.1 AA: 4.5:1 text contrast in both themes, visible focus rings (2px `--brand-primary` offset 2px), full keyboard navigation, skip-link, `aria-label` on icon buttons, `aria-live` for toasts/alerts, heading hierarchy without skips, status never by color alone, `prefers-reduced-motion` honored.

## 10. Governance

- Tokens live in `frontend/src/theme/tokens.css` + `tailwind.config`; this document is their contract.
- New components enter `frontend/src/components/ui/` only if they use tokens exclusively and implement all states (default/hover/focus/disabled/loading/error/empty where applicable).
- Storybook (Phase 5) documents every UI component in both themes; visual review in both themes is part of the definition of done.
- Changes to tokens or this manual require an ADR-lite note in `docs/design/decisions.md`.
