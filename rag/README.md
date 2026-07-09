# rag/

Knowledge Integration / RAG (Phase 14). Consumes and cites external documents — never manages them.

Planned architecture: local/private LLM + local embeddings; pgvector store; chunking with metadata (source system, doc version, permissions); retrieval honoring document ACLs; every answer persists cited chunks + versions (auditable); prompt-injection mitigations on retrieved content; optional knowledge-graph links between characteristics, events and lessons learned.

No customer data leaves the network. No public LLM APIs.
