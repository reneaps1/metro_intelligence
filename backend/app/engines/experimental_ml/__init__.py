"""Experimental, shadow-mode statistical/ML surfaces (roadmap Phase 13:
"Experimental ML -- anomaly detection, drift prediction, adaptive sampling --
offline first, shadow mode", CLAUDE.md §22).

Deliberately isolated from `app.engines.spc`/`app.engines.risk`: nothing here
is imported by the trusted rule-based engines, and nothing here writes an
Alert/Recommendation or otherwise affects a real decision (CLAUDE.md §16).
Every result still stamps `engine_name`/`engine_version` and stays a pure
function, no DB/IO -- same contract as the rest of `app.engines`, just an
explicitly `-experimental` version string that must never be dropped."""
