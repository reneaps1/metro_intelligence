"""F4.5 (MI-25): object storage for raw imported files (MinIO / any
S3-compatible on-premise store -- CLAUDE.md §3 on-premise-first).

``ObjectStorage`` is a narrow Protocol so the import service depends on the
capability, not on the ``minio`` SDK directly -- tests substitute an
in-memory fake via the FastAPI dependency override rather than needing a
real MinIO server."""

from __future__ import annotations

import io
from functools import lru_cache
from typing import Protocol

from minio import Minio

from app.core.config import get_settings


class ObjectStorage(Protocol):
    def put_object(self, bucket: str, object_key: str, data: bytes, content_type: str) -> None: ...


class MinioObjectStorage:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_tls,
        )

    def put_object(self, bucket: str, object_key: str, data: bytes, content_type: str) -> None:
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)
        self._client.put_object(
            bucket,
            object_key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )


@lru_cache
def get_object_storage() -> ObjectStorage:
    return MinioObjectStorage()
