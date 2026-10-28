# process_simulation — simulated injection-moulding signals (IQ-F2)

**Everything here is SIMULATED.** Generic, physics-flavoured profiles for an
injection-moulding cell. Not measurements, not specifications of any real
plant, machine or customer.

## Responsibility

- `catalog.py` — fictitious plant hierarchy (plant → area → line → machine →
  group → channel) and channel definitions (unit, analog/digital, sampling,
  informative vs. negative-control).
- `scenarios.py` — versioned, reproducible scenarios as pure data: `normal`,
  `thermal_drift`, `pressure_setpoint_change`,
  `intermittent_fault_cavity_change`, each with annotated events.
- `generator.py` — cycle timeline (seeded RNG, cached) + pure evaluation of any
  channel at any instant, and windowed series with min/max downsampling.
- `alignment.py` (IQ-F4) — pairs two channels per cycle (simulated
  traceability) or per time with a lag (no traceability), fits OLS via
  `app/engines/statistics`, and scans lags. `cycle_feature` is the
  one-value-per-cycle definition (the value, the profile peak or the in-cycle
  mean).
- `calendar_scenario.py` (IQ-F13) — pure builder of the `real_calendar`
  scenario from plain inputs (piece timestamps, verdicts, nest count, plant UTC
  offset); see below.

Every entry point (`build_timeline`, `generate_series`, `scenario_events`,
`correlate`) takes a `Scenario` object or a static scenario id. A scenario's
optional calendar fields (`start`, `duration_s`, `nest_count`; None = the
fixed 8 h demo calendar with 12 nests) let it run on another calendar; the
static scenarios leave them unset and their output is byte-identical to
`process-sim-1.1.0` (only `GENERATOR_VERSION` moved to `process-sim-1.2.0`).

## "Vista B": synthetic quality with an imposed mechanism

`dim_pins_length` / `dim_nok` (group `quality_sim`, `causal_imposed=true`) are
a synthetic dimension built *from* the process on purpose, to demonstrate the
analysis on known ground truth:
`12.000 + 0.006·Δmold_temp − 0.0006·(hold_pressure − 620) + nest offset + noise`,
tolerance ±0.050 mm, published 300 s after the cycle (inspection delay). In
`intermittent_fault_cavity_change` nest 7 carries a worn insert (+0.04 mm)
until the insert change. Process channels never read this layer (separate RNG
stream), so there is no leakage from quality into process signals.

## "Vista A": process on the real calendar (IQ-F13, plan decision D7)

`build_calendar_scenario` turns the inspected pieces of a dataset into the
`real_calendar` scenario ("Calendario real (simulado)"): start = first piece
floored to the minute, duration = last piece − start + 60 s, downtimes = every
gap ≥ 20 min between consecutive pieces (no cycle starts inside one), nest
count of the dataset on the primary machine (INY-02 keeps the `normal`
behaviour), and a `mold_temp_delta` that follows the hourly NOK rate in plant
time (hours with ≥ 100 pieces, centred 3-hour moving average,
`clamp(4.0·(rate / p_ref − 1), −2, 8)` °C at each hour midpoint, linear in
between, 0 outside). Everything else is the `normal` behaviour.

That delta is derived from real quality labels, so the scenario is
`quality_driven=True`: the API reports `causal_imposed=true` for its mold
temperature, and the delta drives **only** the mold temperature channel (and
the mold-temperature check of `process_ok`) — peak pressure and the Vista B
dimension do not inherit it, so hold pressure, peak pressure and cycle time
remain controls. The scenario is built at runtime
(`app/services/process_join_service.py`, cached per dataset object) and never
added to `SCENARIOS`: no customer dates in code.

## Guarantees

- **Deterministic:** same scenario + machine + instant → same value, whatever
  window or resolution is requested (noise is hashed from the sample index).
- **Stateless:** no database access. Restoring a scenario cannot touch users,
  catalog or measurement history.
- **No leakage:** no parameter of the static scenarios depends on quality
  labels; `process_ok` comes only from the simulated process window. The only
  exception is the declared `quality_driven` calendar scenario above.
- **Bounded output:** ≤ 6 000 evaluations per slow channel and a per-cycle
  envelope for fast channels on long windows; responses capped by `max_points`.

## Boundaries

Served read-only by `app/api/v1/industrial_signals.py` (industrial edition
only). A real source (PLC / OPC UA / iba) would replace this module behind the
same API contract; nothing downstream may assume the data is simulated except
through the `source_type` field.

## Failure history for the experimental prediction study (IQ-F7.b)

`failure_history.py` simulates **9 weeks of hourly history** for four fictitious
machines (`INY-01`…`INY-04`), each with its own seeded RNG
(`random.Random(f"{SEED}:{machine}")`), cached and fully deterministic:

- Latent wear grows every running hour; preventive maintenance (~every 7 days,
  jittered) resets it, corrective repair after a failure only halves it.
- Failures are drawn from an hourly hazard `base + a·wear` (plus a short bump
  after a repair) — **never from the signals**, so signals are effects, not
  causes. ~2 failures per machine-week.
- About 70 % of failures have a precursor (vibration and motor current ramp up
  3–10 h before); the rest have none. Precursor-like bumps with no failure are
  added on purpose so a model has honest false alarms.
- Channels: `vibration_mm_s`, `current_a`, `alarm_count` (Poisson, rate rises
  with vibration). Repair hours are flagged in `downtime` and must be excluded
  from training/evaluation rows.

Consumed by `app/engines/experimental_ml/failure_prediction.py` (temporal
train/test split, pure-Python logistic regression, per-episode evaluation vs.
baselines). Simulated data only — it says nothing about a real machine.

## What-if over the Vista B mechanism (IQ-F7)

`what_if.py` evaluates the **exact** Vista B formula (no fitted model) for a
hold pressure, mold-temperature delta, nest and optional worn insert, and
returns the expected length, P(NOK) as the normal tail outside ±0.050 mm
(spread = measurement noise ⊕ hold-pressure scatter) and sweeps over each
lever. It is HYPOTHETICAL by construction: it says what the simulator would
do. Cycle time is not in the mechanism, so it is not offered as a lever.
