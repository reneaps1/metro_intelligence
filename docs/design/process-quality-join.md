# Process–quality join on the real calendar (IQ-F13, "Vista A")

Step 5 shows two views of the process–quality relationship:

- **Vista B** (IQ-F4): everything synthetic, causal mechanism imposed by the simulator.
- **Vista A** (this document): the customer's REAL dimensional pieces joined **by time**
  with SIMULATED process signals generated on the same calendar. It is an illustrative
  join: there is no cycle/piece traceability between the two sources.

Decision D7 (plan): the simulated `mold_temp` of the calendar scenario follows the
smoothed hourly reject rate of the real data, so a correlation **is imposed by
construction** for that signal. The UI says so; other signals (hold pressure, peak
pressure, cycle time) are not driven by quality and serve as controls (r near 0).
Nothing here is presented as a plant measurement. REAL data stays local (D8): without
the REAL dataset the endpoint answers 404 and the panel explains why.

## Simulator changes (`app/engines/process_simulation/`)

- `Scenario` gains optional calendar fields: `start: datetime | None` (None =
  `SCENARIO_START`), `duration_s: float | None` (None = `SCENARIO_DURATION_S`),
  `nest_count: int | None` (None = `NEST_COUNT`) and `quality_driven: bool = False`.
  `build_timeline`, `evaluate`, `generate_series`, `scenario_events` and the alignment
  helpers accept a `Scenario` object (string ids still work through `get_scenario`).
  **Every existing scenario produces byte-identical output**: seeds, timelines and the
  existing hash/determinism tests stay unchanged.
- `quality_driven=True` maps to `causal_imposed=True` wherever the API reports it.
- Calendar scenarios are built at runtime and never added to the static `SCENARIOS`
  list (no customer dates in code). They are cached by dataset identity.

## Calendar scenario (`real_calendar`)

Built by a pure function from plain inputs (piece timestamps, verdicts, nest count,
plant UTC offset) and wrapped by a service that reads the REAL dataset:

- `start` = first piece time floored to the minute; `duration_s` = last piece − start
  (+ 60 s).
- `downtimes` = every gap ≥ 20 min between consecutive pieces (offset from start,
  duration), so no simulated cycle falls where the real line was stopped.
- `nest_count` = number of nests of the dataset (machine INY-01 = the primary machine
  carries the calendar scenario; INY-02 stays on the `normal` behaviour as today).
- `mold_temp_delta`: hourly NOK rate in plant time (hours with ≥ 100 pieces),
  smoothed with a centred 3-hour moving average; at each hour midpoint
  `delta = clamp(4.0 × (rate_smoothed / p_ref − 1), −2.0, 8.0)` °C, piecewise linear
  between points (0 before the first and after the last point). `p_ref` = NOK rate of
  the whole dataset.
- Everything else (hold setpoint, spikes, faults) = the `normal` scenario.
- `id = "real_calendar"`, name "Calendario real (simulado)", `quality_driven=True`.

## `GET /api/v1/quality-analytics/process-join`

Industrial edition, `measurement.measurement_result:read`.

Query: `dataset` (only `real-dimensional`; anything else 404, REAL absent 404),
`signal` (signal id of INY-01 from the simulator catalog with a per-cycle value, e.g.
mold temperature, hold pressure, peak pressure, cycle time — 422 otherwise), `target`
(`total` or `station:<key>`, same values as the predictive lab — 422 otherwise),
`bucket_minutes` (15, 30 or 60; default 30), `lag_minutes` (−180…180, multiple of
`bucket_minutes`; default 0).

Per bucket of plant time: `x` = mean of the signal's per-cycle values of the cycles
that **start** in `[b − lag, b − lag + bucket)` (positive lag: the process precedes
the inspection); `y` = NOK rate of the dimensional pieces inspected in `[b, b + bucket)`
under the target. A bucket counts only with ≥ 50 pieces and ≥ 5 cycles. Fit with
`app/engines/statistics/regression.linear_fit`.

```json
{
  "dataset": "real-dimensional", "scenario_id": "real_calendar",
  "generator_version": "process-sim-1.2.0",
  "signal": {"id": "...", "name": "...", "unit": "°C"},
  "target": "total", "target_label": "NOK total",
  "bucket_minutes": 30, "lag_minutes": 0, "utc_offset_minutes": -300,
  "n": 0, "pearson_r": null, "slope": null, "intercept": null, "r_squared": null,
  "buckets": [{"start_ts": 0, "x": 0.0, "y": 0.0, "pieces": 0, "cycles": 0}],
  "lag_scan": [{"lag_minutes": 0, "r": null, "n": 0}],
  "best_lag_minutes": null,
  "causal_imposed": true,
  "provenance": ["REAL", "SIMULATED", "EXPERIMENTAL"],
  "notes": ["Unión ilustrativa por tiempo: ...", "..."]
}
```

- `buckets` in time order (also used to draw both series over time); `lag_scan` over
  −180…180 min in steps of `bucket_minutes`; `best_lag_minutes` = lag with the largest
  |r| among lags with n ≥ 10 (null otherwise).
- `causal_imposed` = the calendar scenario is quality-driven **and** the signal is
  mold temperature; for other signals false.
- `notes` (Spanish, shown verbatim): always the illustrative-join warning; when
  `causal_imposed`, "La temperatura de molde simulada se construyó siguiendo la tasa de
  rechazo real: la relación está impuesta por construcción, no medida."; otherwise "Señal
  simulada sin vínculo con la calidad: sirve de control (se espera r cercano a 0)."
- Generator version bumps to `process-sim-1.2.0` (calendar fields); existing outputs
  unchanged.

## Frontend (`QualityJoinPanel`, step 5)

Replaces the "Vista A pendiente" card of `CorrelationPanel`: badges REAL + SIMULATED +
EXPERIMENTAL, banner with the notes, selectors (signal, target, bucket, lag with
"usar desfase óptimo"), cards n / r / R² / slope, scatter with the fitted line and two
stacked time series (NOK rate and the signal mean per bucket, shared time axis, plant
time). Without the REAL dataset: a short explanation instead of the panel.

## Implementation notes (IQ-F13)

- In a `quality_driven` scenario the mold temperature no longer lowers the simulated
  peak pressure (the static scenarios keep that coupling): otherwise peak pressure
  would correlate almost as much as mold temperature and could not serve as a control.
- Signals accepted by the endpoint: INY-01 `mold_temp`, `holding_pressure`,
  `injection_pressure` (peak per cycle) and `cycle_time`; others answer 422. Values per
  cycle are the ones the cycle-mode correlation already uses (`cycle_feature`).
- `target_label` comes from the predictive lab (`target_label()`); verdicts from its
  `target_flags` (a missing verdict counts as OK).
- `buckets` lists only the buckets that count (`n == len(buckets)`); `start_ts` is a UTC
  epoch in seconds.
- Downtimes: no cycle starts inside a stop; a cycle already running finishes.
- Mold delta smoothing averages each qualifying hour with its qualifying neighbours
  (fewer hours at the edges and around stops); the delta is 0 before the first and
  after the last hour midpoint.
- The calendar's nest count applies to INY-01; INY-02 keeps 12 nests and no stops.
  `real_calendar` carries no scripted events (nothing fictitious on the customer's dates).
- `dataset` defaults to `real-dimensional`, `target` to `total`; `signal` is required.
  Validation order: dataset (404), then signal, target, bucket and lag (422).

Out of scope (moved to the plan's pending list): showing `real_calendar` in the step-4
signal explorer and the toolbar scenario picker (needs a long-window envelope).
