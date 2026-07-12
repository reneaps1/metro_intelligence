"""Pydantic request/response models, one module per domain area (catalog,
measurement, context, intelligence, security). Schemas are the only shape
the API layer exposes -- routers never return ORM models directly."""
