# On-Premise Deployment Strategy

Default and first-class deployment: **fully inside customer infrastructure, no internet egress at runtime.**

## Topologies

| Model | Description | When |
|---|---|---|
| 1. 100% on-premise (default) | Single host (Compose) or customer VMs/K8s; local LLM if AI used; internal backups | BMW-class confidentiality |
| 2. Controlled hybrid | Sensitive data on-prem; explicitly authorized private-cloud services; per-flow firewall rules + written authorization | Only with customer sign-off |
| 3. Dedicated private SaaS | Exclusive instance, separate DB, VPN, strong encryption, NDA | Customers without infra |

## Demo footprint

Single host, Docker Compose: reverse proxy (TLS) → frontend + backend; PostgreSQL + MinIO on an internal-only Docker network; ports bound to 127.0.0.1 except the proxy. Segmented Docker networks mirror the zone model (docs/security/network-segmentation.md).

## Production footprint (Phase 15–16)

- Compose-hardened or Kubernetes (customer choice); NetworkPolicies encode zone boundaries.
- TLS via customer PKI; secrets from customer vault or sealed env files with documented rotation.
- Observability: Prometheus + Grafana + log aggregation, all inside Zone Admin.
- Backups: nightly encrypted PostgreSQL base+WAL, MinIO replication, restore drill documented and rehearsed; RPO ≤ 24h, RTO ≤ 4h initial targets.
- Upgrades: versioned images shipped as offline bundles (registry export) — installable air-gapped; Alembic migrations run with backup checkpoint + rollback plan.
- Install runbook + preflight checklist (hardware, OS, firewall rules, AD connectivity) delivered with each release.

## Air-gap rules

- No external CDNs: fonts, JS, icons all self-hosted (design system already mandates this).
- License/update checks: none that require egress.
- ML/RAG: models packaged and loaded locally.
