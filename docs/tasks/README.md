# docs/tasks/ — Task handoff packets

Each file in this folder is a **self-contained handoff** for one Notion task (Metro Intelligence — Plan de desarrollo). A fresh agent — or a human developer — should be able to open a new session, read only that one file, and execute the task correctly with zero other context.

These cover the 24 remaining **Demo core** tasks as of 2026-07-11 (everything needed to take the demo from mock data to a real, working backend + frontend). They do **not** cover Demo soporte or Post-demo tasks — check the Notion database for those.

## How to use one of these files

1. **Read `CLAUDE.md` at the repo root first, in full.** It is the binding operating guide (architecture, security, git rules, RBAC, testing, everything). Every rule in it applies to every task regardless of what's repeated below.
2. Read the "Referencias obligatorias" section in the task file — these are the specific docs that task needs beyond CLAUDE.md.
3. Check the "Dependencias" section's status. If a dependency says "PR abierto, no mergeado", either wait for it to merge or branch from that PR's branch instead of `main` (ask the user which if unsure — don't guess silently).
4. Follow the branch/commit/PR workflow below.
5. Update the Notion task page when you finish (link in each file).

## Standard workflow (every task)

```bash
git checkout main && git pull origin main
git checkout -b feat/mi-<NN>-<slug> main   # branch naming per CLAUDE.md §8
# ... do the work ...
git add <files touched — never `git add .` in a dirty worktree>
git commit -m "feat: <summary> (F<phase>.<n>)"   # Conventional Commits, reference the Notion task ID
git push -u origin feat/mi-<NN>-<slug>
gh pr create --base main --head feat/mi-<NN>-<slug> --title "..." --body "..."
```

Then update the task's Notion page: add a delivery note with the PR link, and set Status to `In progress` (if verification is still pending) or `Done` (if you actually ran the tests against a real environment and they pass).

## Non-negotiable rules (repeated here because they matter most)

- **Never merge a PR without the user's explicit, current authorization.** CLAUDE.md §8 requires PR + review before merge to `main`. If you wrote the code yourself and haven't run it against a real Postgres/browser, say so explicitly in the PR description — don't imply it's verified when it isn't.
- **No hardcoded secrets, ever.** Config via env vars, documented in `.env.example`.
- **RBAC on every new endpoint** — check `docs/security/rbac.md` for the exact role×resource×action matrix.
- **Migrations only via Alembic**, one head, no parallel migration chains — check `backend/alembic/versions/` for the current head before adding a new revision.
- **All demo data is fictitious** (`MI-DEMO-*`, `.demo.local` emails) — never anything resembling a real BMW/OEM identifier.
- If you can't run something in your environment (no Docker, no Python, no browser) — say so plainly in the commit/PR rather than claiming untested work is verified. This has been the norm throughout this project's history so far; keep it up.

## Important shortcut: the mock frontend already exists

`frontend/` currently contains a **fully working mock-data demo** (F5.M, merged to `main`): login, catalog, measurements with SPC trend charts, risk heatmap, recommendations accept/reject, operational + executive dashboards, file import simulation — all wired to static fixtures in `frontend/src/lib/mock/` behind a `useDemoData()` hook, not a real API.

**For every F5.x/F6.x task below: read the existing mock implementation first.** Several of these tasks are largely "replace the mock data source with real API calls behind the same UI" rather than building a screen from scratch. Each task file below says explicitly which existing mock file(s) are the starting point.

## Task index

| File | Notion ID | Task |
|---|---|---|
| F3.4.md | MI-19 | Seed: process events, demo users, decision history |
| F3.5.md | MI-20 | Seed validation suite + sample import files |
| F4.1.md | MI-21 | FastAPI skeleton |
| F4.2.md | MI-22 | JWT auth + RBAC + rate limiting |
| F4.3.md | MI-23 | Audit service |
| F4.4.md | MI-24 | Catalog CRUD API |
| F4.5.md | MI-25 | File import pipeline API |
| F4.6.md | MI-26 | Measurements read API |
| F4.8.md | MI-28 | Recommendations/decisions API |
| F5.1.md | MI-30 | Frontend scaffold (mostly already done by F5.M — see file) |
| F5.3.md | MI-32 | Navigation shell (mostly already done by F5.M — see file) |
| F5.4.md | MI-33 | Real login/JWT session (replaces F5.M's mocked login) |
| F5.5.md | MI-34 | Catalog screens (wire to real API) |
| F5.6.md | MI-35 | Import screen (wire to real API) |
| F5.7.md | MI-36 | Measurements screens (wire to real API) |
| F5.9.md | MI-38 | Recommendations inbox (wire to real API) |
| F6.1.md | MI-39 | SPC chart component library (mostly already done by F5.M — see file) |
| F6.2.md | MI-40 | Operational dashboard (wire to real API) |
| F6.3.md | MI-41 | Executive dashboard (wire to real API) |
| F7.D.md | MI-44 | Compliance engine (demo) |
| F8.D.md | MI-45 | SPC engine (demo) |
| F9.D.md | MI-46 | Risk engine (demo) |
| F10.D.md | MI-47 | Adaptive inspection engine (demo) |
| LM1-live-monitor-mvp.md | — (no Notion page; see `docs/design/live-monitor-panel.md`) | Live Monitor Fase 1/4: replay backend + WebSocket + grid frontend |
| LM2-live-monitor-detail-view.md | — (no Notion page) | Live Monitor Fase 2/4: vista de detalle explicable (depende de LM1) |
| LM3-live-monitor-presenter-controls.md | — (no Notion page) | Live Monitor Fase 3/4: controles de presentador (depende de LM1/LM2) |
| LM4-live-monitor-deep-dive.md | — (no Notion page) | Live Monitor Fase 4/4: página de detalle completa, límites de control históricos + navegación temporal (depende de LM1, lógicamente de LM2) |

(F3.3 — measurement series generator — already has an open PR, #7, pending review/merge; no handoff file needed since it's essentially done.)

The four `LM*` files are a demo-enhancement feature (a SCADA-style live measurements panel) that came out of a brainstorming session, not from the original Notion phase plan — no Notion tickets exist for them yet. Design doc: `docs/design/live-monitor-panel.md`. Run them in order (LM1 → LM2 → LM3 → LM4); each depends on the previous one's PR (LM4 depends on LM1 directly, and on LM2 only for its natural entry point, not a hard blocker).
