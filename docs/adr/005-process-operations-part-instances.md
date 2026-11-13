# ADR-005: Process operations, part instances and per-step results

**Status:** Accepted · 2026-11-13

## Context
A production line inspects every piece at several stations in sequence (electrical tests, pin length, pin position, type check). Each station exports one row per piece, keyed by a sequential piece id that is shared across stations. Users need results **per process step** and must be able to follow one piece through all steps. The existing model has `Line`/`Machine`, catalog characteristics and `MeasurementRun → MeasurementSample → MeasurementResult`, but no notion of a step sequence, a recipe, or a physical piece seen by several stations.

## Decision
New entities (`backend/app/models/process.py`, migration `0009_process_model`), named after the conceptual model (`Process`/`Operation`):

| Entity | Meaning |
|---|---|
| `Operation` (`process_operations`) | One step of a line, with a `sequence`, an `operation_kind` (`electrical`, `pin_length`, `pin_position`, `type_check`), an optional `side` (`pcb`, `connector`) and the `Machine` that runs it. |
| `Recipe` (`process_recipes`) | The machine program that identifies the product variant (e.g. recipe 2). `variant_part_number_id` and `variant_label` are nullable and set later by `relabel_recipe`, so the variant name can change without reloading data. |
| `PartInstance` (`process_part_instances`) | One physical piece, identified by its serial (the station piece id) on a line, with its recipe. |
| `StepResult` (`process_step_results`) | One station row for one piece: time, nest, machine verdict, attempt number. Linked 1:1 to the `MeasurementSample` that holds its values. |

Rules:
- **Measurement history stays immutable.** Per-pin values are `MeasurementResult` rows. Repeated station rows for the same piece are new `StepResult`s with `attempt_no = n + 1`; nothing is updated or dropped.
- **Two verdicts are kept apart.** `MeasurementResult.machine_ok` / `machine_code` store what the station decided. `is_ok` / `deviation` / `specification_id` store the compliance engine's verdict against the specification in force at `measured_at`. When no specification exists both compliance fields are NULL; no limit is invented.
- **One-sided specifications.** Pin position uses the GD&T zero-nominal convention (nominal 0, `upper_tol` = tolerance). A "maximum X" length with no nominal is stored as nominal = X, `upper_tol` = 0, `lower_tol` NULL, so `deviation` is the margin to the limit.
- **Derived statistics are not history.** `process_step_daily` and `process_characteristic_daily` hold daily moments (n, sum, sum of squares, min, max, NOK counts) per step, recipe, nest and characteristic. They are rebuilt by `build_daily_stats` (recorded in `process_stats_builds`) and are how dashboards stay fast over tens of millions of results. Re-evaluating against a new specification version means rebuilding these tables, never updating results.
- Filler values for positions that do not exist on a product are not loaded.
- **Gross readings stay out of the moments.** A value more than 10 tolerance bands beyond its limit (`GROSS_BAND_FACTOR` in `app/ingest/stats.py`) is a measurement failure, such as a lost pin or a wrong edge, not process spread. It stays in `n`, in the NOK counts and in `min`/`max`, and is counted in `n_gross`; only the sum and the sum of squares leave it out. Mean, standard deviation and capability then describe the process, and every view that shows them says how many readings were left out. The rule needs a specification with a non-zero band; without one nothing is excluded. Results are never changed: the factor is recorded in `process_stats_builds` and a rebuild applies a new one.
- **A partial record carries no status.** A step that recorded under half of the pieces seen at type check in the selected range (`PARTIAL_COVERAGE` in `app/services/process_status.py`) is shown as "Partial log" with its coverage. Its rates describe a sample, so it is left out of the line's worst step, rolled yield and daily trend.
- **Rolled yield.** The line-level yield is the product of the pass rates of the fully recorded steps, using the drawing verdict where a specification exists and the station verdict otherwise. It assumes the steps fail independently and is labelled with the number of steps it covers.

## Consequences
+ Per-step KPIs, piece traceability and recipe filtering come from explicit, indexed entities.
+ Capability (Cp, Cpk, Cpu) is computed from moments, so it scales without loading raw values.
− `measurement_results.specification_id` becomes nullable (reference and electrical values have no specification).
− Daily tables must be rebuilt after each load or specification change.
