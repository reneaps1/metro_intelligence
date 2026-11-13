# line_alarms — line quality panel rules (IQ-F14)

Pure engine, no DB/IO, version `v1-experimental` (shadow mode: an alarm asks a
person for an action, it never acts on production). Contract and rationale:
`docs/design/line-quality-panel.md`.

- `rules.py` — `evaluate_line(timestamps, nests, mold_cavities, nok, stations,
  config, reference_nok_rate)` replays four rules after each piece, in line
  order, with running counters (O(nests + cavities) per piece):
  - **R1** NOK streak (priority 1): `run_limit` consecutive NOK; clears on the next OK.
  - **R2** nest out of pattern (priority 2): a nest's last `nest_window` pieces
    reach `nest_factor` × the pooled rate of the other nests' windows and at
    least `nest_min_nok` NOK.
  - **R3** high NOK rate (priority 2): last `rate_window` line pieces reach
    `rate_factor` × `p_ref`.
  - **R4** mold cavity (priority 3, advisory): a cavity's last `cavity_window`
    pieces reach `cavity_factor` × `p_ref`; only when the line has mold cavities.

  Returns per-piece state (`run`, `rate`, worst nest ratio, worst cavity rate)
  and every alarm event (raise / clear / evidence indices, value, peak in
  hindsight, limit, nest of each streak piece, first failing station).

## Definitions

- `p_ref` = NOK rate of the whole evaluated sequence (hindsight reference),
  unless the caller passes one. Thresholds are relative to it.
- Rate rules need a full window and at least one NOK in it.
- The pooled rate of the other nests counts at least half a NOK, so the R2
  ratio stays finite when the other nests had none.

Composition with datasets (line order, machine filter, caching, moments and
replay windows) lives in `app/services/line_panel_service.py`.
