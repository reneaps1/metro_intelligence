# quality_analytics — dimensional quality aggregations (IQ-F5)

Pure engines, no database access.

- `dataset.py` — `DimensionalDataset`: columnar, source-agnostic (one row per
  inspected piece; machine / cavity / shift / batch columns may be missing,
  and `available_filters()` says which ones exist). IQ-F6 CSV imports
  (`app/connectors/dimensional_csv.py`) produce one of these with
  `source_type="IMPORTED"`; every analytic works unchanged. An imported file
  may carry its own verdict (`reported_nok`), which `overview()` compares with
  the recalculated one (`summary.source_reported`) instead of merging them.
  `Variable.from_limits()` builds a variable from absolute limits; without a
  nominal in the source, `display_nominal` is `None`.
- `synthetic.py` — the demo dataset: **SIMULATED**, deterministic (fixed seed),
  7 days × 2 machines × 12 nests × 10 dimensions, with documented mechanisms
  (critical nest via `DEMO_CRITICAL_NEST`, NOK waves, tool wear + tool change,
  night-shift spread, batch shrink). `mechanisms` lists the injected truth.
- `analytics.py` — `overview()` (KPIs, trend by day/hour/shift, Pareto,
  per-nest rate with Wilson 95 % CI and relative risk, nest × variable
  heatmap) and `variable_detail()` (histogram, boxplots by group, Cp/Cpk and
  I-MR limits via `app/engines/spc`, daily Cpk).
- `process_join.py` (IQ-F13, "Vista A") — illustrative join BY TIME of piece
  verdicts with per-cycle process values on plant-time buckets: `x` = mean of
  the cycles that start in `[b − lag, b − lag + bucket)`, `y` = NOK rate of the
  pieces inspected in `[b, b + bucket)`; a bucket counts with ≥ 50 pieces and
  ≥ 5 cycles; OLS fit, lag scan and best lag (largest |r| with ≥ 10 buckets).
  There is no cycle/piece traceability behind it. Composed with the REAL
  dataset and the simulated `real_calendar` scenario by
  `app/services/process_join_service.py`.

## Definitions (returned with the data)

- Measurement NOK: value outside tolerance. Piece NOK: any selected variable NOK.
- Relative risk of a nest: its piece NOK rate / pooled rate of the other selected
  nests. Association, not cause.
- Cp needs a bilateral tolerance; without tolerances no capability is reported.
- Specification limits (LSL/USL) and control limits (UCL/LCL) are separate fields.
