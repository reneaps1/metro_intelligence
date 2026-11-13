Deployments run on real line data loaded through the ingest CLIs (ADR-004), not on demo seeds.
Container startup only runs migrations and the API; it never loads or resets data.
To remove domain data while keeping users, roles, permissions and the audit log:
`python -m app.cli.purge_domain_data --dry-run`, then `--confirm` (take a `pg_dump` first).
