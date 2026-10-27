# quality_analytics — dimensional quality aggregations (IQ-F5)

Pure engines, no database access.

- `dataset.py` — `DimensionalDataset`: columnar, source-agnostic (one row per
  inspected piece; machine / cavity / shift / batch columns may be missing,
  and `available_filters()` says which ones exist). IQ-F6 imports produce one
  of these; every analytic works unchanged.
- `synthetic.py` — the demo dataset: **SIMULATED**, deterministic (fixed seed),
  7 days × 2 machines × 12 nests × 10 dimensions, with documented mechanisms
  (critical nest via `DEMO_CRITICAL_NEST`, NOK waves, tool wear + tool change,
  night-shift spread, batch shrink). `mechanisms` lists the injected truth.
- `analytics.py` — `overview()` (KPIs, trend by day/hour/shift, Pareto,
  per-nest rate with Wilson 95 % CI and relative risk, nest × variable
  heatmap) and `variable_detail()` (histogram, boxplots by group, Cp/Cpk and
  I-MR limits via `app/engines/spc`, daily Cpk).

## Definitions (returned with the data)

- Measurement NOK: value outside tolerance. Piece NOK: any selected variable NOK.
- Relative risk of a nest: its piece NOK rate / pooled rate of the other selected
  nests. Association, not cause.
- Cp needs a bilateral tolerance; without tolerances no capability is reported.
- Specification limits (LSL/USL) and control limits (UCL/LCL) are separate fields.
