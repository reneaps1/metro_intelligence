# Security Architecture

Confidentiality is a primary requirement: the customer is a high-end automotive OEM and all measurement/process data is potentially strategic. Design stance: **on-premise first, deny by default, least privilege, everything auditable.**

## 1. Threat model (summary)

| Asset | Threats | Primary controls |
|---|---|---|
| Measurement data & tolerances (customer IP) | Exfiltration, unauthorized access | On-premise deployment, RBAC, TLS, encryption at rest, audit log, no external calls by default |
| Master catalog | Tampering (changing tolerances → false OK) | Versioned specs, RBAC on writes, audit trail, immutable history |
| Recommendations/decisions | Repudiation, manipulation | Immutable decision trail, signed/append-only audit records |
| Uploaded files | Malicious files (parser exploits, macros, zip bombs) | Type/size/content validation, parse in constrained code path, never execute, store raw in isolated bucket |
| API | Injection, brute force, abuse | ORM-parameterized queries, rate limiting on auth/upload, input validation (Pydantic), security headers |
| Credentials/secrets | Leakage via repo/logs | .env only, gitignore, secret scanning in CI, no secrets in logs, rotation procedures |
| Containers/dependencies | Supply chain, CVEs | Pinned images, non-root containers, pip-audit/npm audit in CI, minimal base images |

## 2. Identity & access

- **Demo:** local users, salted+hashed passwords (argon2/bcrypt), JWT access+refresh, RBAC middleware.
- **Enterprise (Phase 11):** SSO via LDAP/Active Directory or SAML/OIDC against customer IdP; MFA delegated to IdP where applicable.
- **RBAC roles (initial):**
  - `viewer` — dashboards and reports, read-only.
  - `metrologist` — imports, measurement runs, view recommendations.
  - `quality_engineer` — accept/reject recommendations, manage inspection plans.
  - `admin` — master data, users, connectors, configuration.
  - `auditor` — read-only including audit logs.
- Deny by default: every endpoint declares required permission; unauthenticated access only for `/health` and login.

## 3. Data protection

- **In transit:** TLS everywhere (reverse proxy terminates; internal TLS in production hardening phase).
- **At rest:** PostgreSQL on encrypted volumes (LUKS/BitLocker per customer standard); MinIO SSE; backups encrypted.
- **Classification:** all measurement/master data treated as *Confidential — Customer IP* by default.
- **Data never leaves the customer network** in default deployment. Hybrid options require explicit written authorization per data category.
- Demo/seed data is fictitious by construction; CI test rejects real-looking identifiers.

## 4. Audit & traceability

- Append-only `audit_log`: logins/failures, permission changes, master-data changes (before/after), imports, recommendation lifecycle, decisions.
- Decision traceability chain (CLAUDE.md §23) stored relationally and never updated in place.
- Log integrity: application logs shipped to a write-restricted store; production option for hash-chained audit records.

## 5. Application security

- Pydantic validation on all inputs; explicit allowlists for file types (initially: .csv, .xlsx, PolyWorks text exports).
- File uploads: size caps, MIME + magic-byte check, parse with hardened libs, quarantine on failure; stored in MinIO with random object names.
- Rate limiting (slowapi/nginx) on `/auth/*` and `/imports/*`.
- Security headers (CSP, HSTS, X-Content-Type-Options) at the reverse proxy.
- Error hygiene: no stack traces, SQL, or paths in responses.
- SQL injection prevention: SQLAlchemy ORM/parameterized only; raw SQL requires review.

## 6. Platform & pipeline security

- Containers: non-root user, read-only FS where possible, pinned versions, minimal images (alpine/distroless).
- CI (GitHub Actions): lint, tests, `pip-audit`, `npm audit`, secret scanning (gitleaks), container scan (trivy) before image publish.
- Branch protection on `main`: PR + passing CI + review required.
- Environments separated: dev / staging / customer-prod; separate credentials, no shared secrets.
- Backups: scheduled pg_dump/base backups + MinIO replication inside customer infra; documented restore drills (DR plan in Phase 15).

## 7. AI-specific security (Phases 13–14)

- LLM/embeddings: local or explicitly authorized private endpoints only; no customer data to public APIs.
- RAG: document-level ACLs honored at retrieval; answers persist cited chunks + versions; prompt-injection mitigations on retrieved content.
- Model registry with access control; model inputs/outputs logged for audit.
