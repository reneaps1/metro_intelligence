# ADR-001: Modular monolith for MVP

**Status:** Accepted · 2026-07-08

## Context
The demo and MVP must be installable on a single on-premise host, developed fast by parallel agents, and must not accumulate operational complexity the customer's IT would have to run.

## Decision
One FastAPI application with strict internal module boundaries (`api`, `engines`, `connectors`, `services`, `repositories`, `models`). No microservices, no message broker in the demo. Extraction into services only when a concrete scale/isolation need appears, via a new ADR.

## Consequences
+ Single deployable, simple ops, easy on-prem install, fast iteration.
+ Module boundaries keep future extraction possible (engines are already pure).
− Requires discipline: cross-module imports only through declared interfaces; CI can add import-linting later.
