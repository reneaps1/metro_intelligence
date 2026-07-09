# infra/

Deployment & operations assets.

- `nginx/` — reverse proxy config (TLS, security headers, rate limiting) — the only exposed service.
- `monitoring/` — Prometheus + Grafana configs (Phase 15).
- `k8s/` — optional Kubernetes manifests incl. NetworkPolicies mirroring docs/security/network-segmentation.md (Phase 15+).
- `backup/` — backup/restore scripts and runbooks.

Docker networks in the root docker-compose.yml emulate the security zones (net_dmz / net_app / net_data).
