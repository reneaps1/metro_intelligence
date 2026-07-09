# ADR-003: PostgreSQL 16 as primary database

**Status:** Accepted · 2026-07-08

## Context
Candidates: PostgreSQL vs SQL Server. Requirements: on-premise installs without per-customer licensing friction, versioned master data, high-volume measurement history, future vector search for RAG.

## Decision
PostgreSQL 16. `pgvector` reserved for the RAG phase (Qdrant only if scale demands, via ADR). Time partitioning planned for `measurement_result`.

## Rationale
- Zero license cost per on-prem deployment; runs identically in Compose/K8s/air-gapped.
- JSONB for flexible context/factor payloads; native partitioning; mature backup/replication tooling.
- pgvector keeps RAG inside the same hardened database instead of adding a new service.

## Consequences
− Customers standardized on SQL Server may push back; mitigated: containerized, we operate it, documented backup story.
