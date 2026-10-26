# industrial-analytics — signal explorer and correlation (IQ-F3, IQ-F4)

Industrial edition only. Consumes `/api/v1/industrial-signals/*`; every value
shown here is **SIMULATED** (see `backend/app/engines/process_simulation`).

- `SignalExplorer.tsx` — iba-style explorer: tree with drag & drop (+ "Agregar"
  fallback), one track per unit or multi-axis overlay, brush/toolbar zoom, pan,
  A/B cursors (click or sliders), event markers `E<n>`, replay.
- `SignalTree.tsx`, `TrackChart.tsx`, `SignalTable.tsx` — its parts.
- `CorrelationPanel.tsx` — scatter, OLS, Pearson r, lag scan; wording stays at
  "association", and synthetic "Vista B" channels are labelled as imposed.

Pure logic (reducer, unit grouping, cursor interpolation, zoom math, wording)
lives in `src/lib/industrial-signals/` and is unit-tested there. Cursor values
read from a min/max envelope are shown as approximate (`≈`).
