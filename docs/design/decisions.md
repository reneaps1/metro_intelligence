# Design decisions (ADR-lite)

Short records of changes to `design-system.md` or `frontend/src/theme/tokens.css` (design-system.md §10).

## 2026-10-26 — Engineering workbench for the industrial demo

- **Context:** the industrial demo needed to feel like a robust desktop engineering tool, not a generic web dashboard. Five interface proposals were reviewed; the owner chose proposal 3 ("Ingeniería Ribbon", TIA Portal / iba Analyzer style) with light and dark mode.
- **Decision:** the `/demo/industrial-quality` module renders full-viewport in a workbench layout (title strip, command ribbon, docked navigator / properties / output panes, status bar). Spec: design-system.md §4.1. Eight `--wb-*` chrome tokens added with light and dark values; accents reuse `--brand-accent`.
- **Scope:** industrial edition demo module only. Platform sidebar/top bar, metrology edition and all other screens are unchanged.
- **Exception:** ribbon and title-strip targets are ≥32px instead of 44px (desktop pointer use only).
- **Consequences:** step content components are unchanged and already theme-aware through the semantic tokens. Extending the workbench to other modules requires a new note here.

## 2026-10-28 — Workbench refined: one place per fact, ISA-101 color

- **Context:** the owner found the ribbon workbench redundant (navigation in four places, scenario in four, step position in three, provenance chip on every panel) and chose proposal "E2" from a new review grounded in Apple HIG and ISA-101 (high-performance HMI).
- **Decision:** menu bar (command index) + toolbar (path, scenario, alarms, `‹ n / 7 ›`) + two-level project tree + inspector (technical details of the view) + status bar (connection, last action). Ribbon, properties pane and output log removed; steps 4/5 show the scenario read-only. Scenario changes take two actions (choose, Aplicar) and can be undone; they never navigate. Re Pág / Av Pág walk the demo. Simulated alarms (`lib/demo/alarms.ts`) illustrate priority, acknowledge and summary, labeled "Simulada". Spec: design-system.md §4.1.
- **Color:** neutral grays scoped to `.wb-root` in `tokens.css` (dark `#2B3036`, not near-black); status colors re-tuned there to keep ≥4.5:1. `OriginBadge` becomes neutral everywhere (icon + label; Experimental dashed): provenance is metadata, so it no longer borrows the warning/NOK colors. Simulated now uses the waveform icon (Cpu stays for machines).
- **Consequences:** chart tolerance lines inside step content still use `--status-nok` (design-system §1.4); aligning them with "alarm colors only for alarms" is pending. Per-panel technical details in the inspector need panel-level selection in each step (pending).
