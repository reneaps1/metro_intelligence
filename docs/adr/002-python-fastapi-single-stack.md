# ADR-002: Python 3.12 + FastAPI single stack

**Status:** Accepted · 2026-07-08

## Context
The platform's core value is statistical/decision logic (SPC, risk, adaptive sampling) plus future ML/RAG. Candidates: FastAPI (Python) vs .NET 8.

## Decision
Python + FastAPI for the entire backend, engines, ML and RAG.

## Rationale
- SPC/ML/RAG live in the Python ecosystem (numpy, scipy, statsmodels, scikit-learn, pandas); a .NET backend would force a second stack and double the security/deploy surface.
- One language → one toolchain, one container base, simpler audits and dependency scanning for on-prem customers.
- Security is achieved by hardening (RBAC, validation, scanning, segmentation — see docs/security/), not by runtime choice; FastAPI + Pydantic gives strong input validation by default.

## Consequences
− Windows-centric customer IT may expect .NET; mitigated by shipping containers.
− CPU-bound throughput lower than .NET; irrelevant at metrology data volumes, revisit with load tests in Phase 15.
