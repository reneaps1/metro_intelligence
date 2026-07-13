"""Compliance, SPC, risk, adaptive inspection, recommendation, and decision
memory engines (CLAUDE.md §3). Every engine is a pure function: data in,
result out, no DB/HTTP access and no side effects -- persistence is the
calling service's job, via repositories/. Rule-based first; ML augments
later, never silently replaces rules (CLAUDE.md §22)."""
