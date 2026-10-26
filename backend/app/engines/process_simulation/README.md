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
  `app/engines/statistics`, and scans lags.

## "Vista B": synthetic quality with an imposed mechanism

`dim_pins_length` / `dim_nok` (group `quality_sim`, `causal_imposed=true`) are
a synthetic dimension built *from* the process on purpose, to demonstrate the
analysis on known ground truth:
`12.000 + 0.006·Δmold_temp − 0.0006·(hold_pressure − 620) + nest offset + noise`,
tolerance ±0.050 mm, published 300 s after the cycle (inspection delay). In
`intermittent_fault_cavity_change` nest 7 carries a worn insert (+0.04 mm)
until the insert change. Process channels never read this layer (separate RNG
stream), so there is no leakage from quality into process signals.

## Guarantees

- **Deterministic:** same scenario + machine + instant → same value, whatever
  window or resolution is requested (noise is hashed from the sample index).
- **Stateless:** no database access. Restoring a scenario cannot touch users,
  catalog or measurement history.
- **No leakage:** no parameter depends on quality labels; `process_ok` comes
  only from the simulated process window.
- **Bounded output:** ≤ 6 000 evaluations per slow channel and a per-cycle
  envelope for fast channels on long windows; responses capped by `max_points`.

## Boundaries

Served read-only by `app/api/v1/industrial_signals.py` (industrial edition
only). A real source (PLC / OPC UA / iba) would replace this module behind the
same API contract; nothing downstream may assume the data is simulated except
through the `source_type` field.
