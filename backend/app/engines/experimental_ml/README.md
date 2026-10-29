# experimental_ml — shadow-mode statistics and models

Roadmap phase 13 surfaces (CLAUDE.md §22). Pure functions, no DB/IO, every
engine stamps a `-experimental` version. Nothing here is imported by the
trusted rule-based engines, writes an Alert/Recommendation or acts on
production: outputs are hints for human review.

- `drift_cusum.py` — two-sided, self-starting CUSUM with every intermediate
  returned (Live Monitor; IQ-F7 also runs it over hourly synthetic series).
- `nok_waves.py` (IQ-F7) — persistence rule ("≥ k NOK in the last w groups",
  past data only) evaluated per independent episode: anticipated vs. detected
  after the start vs. missed, delay, share of the wave still ahead, debounced
  false alarms. Detecting a started streak is not predicting its start.
- `failure_prediction.py` (IQ-F7.b) — features from past hours only,
  pure-Python logistic regression (IRLS), temporal train/test split,
  baselines on the same test rows, per-episode evaluation and per-threshold
  metrics over the simulated history in
  `app/engines/process_simulation/failure_history.py`.
- `nok_waves.retrospective_episodes` (IQ-F12) — episodes of a REAL series
  labelled with hindsight ("≥ k NOK in the next w pieces"), only to evaluate
  the persistence rule; never used as an input.
- `group_alarms.py` (IQ-F12) — per-group (mold cavity / nest) alarm rule
  "≥ k NOK in the last n pieces of the group", replayed in time order: first
  alarm, NOK before/after it, OK pieces reviewed while in alarm.
- `piece_risk.py` (IQ-F12) — per-piece risk from the past of each piece only
  (recent group, second-group and line NOK rates), logistic regression reused
  from `failure_prediction`, last plant-local day as test, compared with two
  transparent baselines; rank-based ROC-AUC.

Composition with datasets lives in services
(`app/services/drift_detection_service.py`, `app/services/predictive_service.py`,
and `app/services/real_predictive_service.py` for the local REAL dataset).
