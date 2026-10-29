# quality-analytics — dimensional quality dashboard (IQ-F5)

Industrial edition only; consumes `/api/v1/quality-analytics/*`.

- `QualityOverview.tsx` (demo step 2) — KPIs with denominators and CI, NOK trend
  (day / hour / shift), Pareto, NOK by nest with 95 % CI and relative risk,
  nest × variable heatmap, PRECOMPUTED historical-report block, and the
  synthetic dataset's "known truth".
- `DimensionalExplorer.tsx` (step 3) — one variable: histogram with tolerances,
  boxplots by nest / machine / shift / batch, I-MR chart (specification and
  control limits drawn and labelled differently), daily Cpk.
- `QualityFilterBar.tsx` — coordinated filters kept in the demo session
  (`lib/demo/DemoSessionProvider.tsx`); filters the dataset cannot support are
  disabled with an explanation.

Query building, CSV export and formatting live in `src/lib/quality-analytics/`.
