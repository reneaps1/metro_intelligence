# ml/

Experimental ML (Phase 13 — not before a solid data foundation exists). Offline/shadow mode first; rules-based engines remain the baseline and fallback (CLAUDE.md §22).

Planned: anomaly detection on measurement series, drift prediction, NOK-risk classification, adaptive sampling policy models, feature-importance ranking. Models versioned in a registry with access control; training data lineage recorded.

- `notebooks/` — exploration (no customer data, seed/derived data only).
- `experiments/` — reproducible training scripts + configs.
- `models/` — artifacts (gitignored).
