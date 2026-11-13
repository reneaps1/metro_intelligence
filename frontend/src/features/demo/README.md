# demo — guided industrial-quality walkthrough (IQ-F1…F8)

Industrial edition only (`RequireEdition edition="industrial"`); the route is
`/demo/industrial-quality/*` and the metrology edition never mounts it.

- `DemoShell.tsx` — layout of the walkthrough: stepper, previous/next and
  "Restaurar escenario demo" (resets client state only, never the database).
- `DemoHomePage.tsx` — start button, quick access and the provenance legend.
- `DemoStepPage.tsx` — step header with provenance badges and the step body.
  Chart-heavy steps are `lazy()` chunks. Steps 2/3 switch their badges to
  HISTORICAL when an imported CSV is selected.
- `steps/` — one component per step: `ContextStep` (1), `QualitySteps` (2, 3;
  dataset picker + CSV import), `IiotLabStep` (4), `CorrelationStep` (5),
  `AiStep` (6, panels in `features/predictive/`), `IntegrationStep` (7).

Step metadata (titles, origins) lives in `lib/demo/steps.ts`; session state
(scenario, quality filters) in `lib/demo/DemoSessionProvider.tsx`. Presenter
guide: `docs/demo-industrial-quality.md`.
