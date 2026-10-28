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

## 2026-10-28 — Line quality panel: three views on a replay of the line

- **Context:** the owner asked for a production-level quality panel (pieces produced, OK, NOK) that triggers action ("5 NOK in a row: stop the line"), full screen, simple commands, in the current industrial style. Three proposals were prototyped outside the repo; the owner kept all three as views of one panel.
- **Decision:** full-screen route with views A Andon / B Process map / C Guided response (design-system.md §4.2). Data: the backend replays the active dimensional dataset piece by piece and a rule engine (`line_alarm_engine`, R1–R4, thresholds relative to the line's historical NOK rate) decides when each rule fires (`docs/design/line-quality-panel.md`). The presenter's Normal / Atención / Paro buttons jump to real moments of the data instead of injecting simulated stops, so measured and simulated data are never mixed.
- **Color:** new `--lp-*` tokens scoped to `.wb-root`; alarm colors only where the operator has to act (single NOK pieces stay neutral).
- **Consequences:** acknowledgements and actions are session state of the replay and are not persisted; a real deployment would feed them to Decision Memory (CLAUDE.md §23). Shifts are 8 h blocks from 06:00 until the customer's schedule is known.
