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

Composition with datasets lives in services
(`app/services/drift_detection_service.py`, `app/services/predictive_service.py`).
