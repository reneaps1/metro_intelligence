"""JWT issuing/verification and RBAC FastAPI dependencies (deny-by-default,
per docs/security/rbac.md) land here in F4.2 (MI-22). Out of scope for F4.1
(MI-21) -- this file exists only to establish the module boundary
backend/README.md defines, so F4.2 has a clear home rather than another
agent guessing where auth code belongs."""
from __future__ import annotations
