# app/modules/reports/storage.py
import asyncio
from functools import lru_cache
from io import BytesIO
from typing import Protocol

from app.core.settings import settings


class ObjectStorage(Protocol):
    async def put(self, key: str, data: bytes, *, content_type: str) -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...


class InMemoryObjectStorage:
    """Test/fallback storage. Not persistent."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        self._store[key] = data

    async def get(self, key: str) -> bytes:
        return self._store[key]  # raises KeyError if absent

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)


class MinioObjectStorage:
    """MinIO-backed storage. The minio client is blocking, so each call runs in a
    worker thread to stay friendly to the event loop."""

    def __init__(self, client, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        await asyncio.to_thread(
            lambda: self._client.put_object(
                self._bucket, key, BytesIO(data), len(data),
                content_type=content_type,
            )
        )

    async def get(self, key: str) -> bytes:
        def _get() -> bytes:
            resp = self._client.get_object(self._bucket, key)
            try:
                return resp.read()
            finally:
                resp.close()
                resp.release_conn()
        return await asyncio.to_thread(_get)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._client.remove_object, self._bucket, key)


@lru_cache(maxsize=1)
def _minio_storage() -> MinioObjectStorage:
    from minio import Minio

    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)
    return MinioObjectStorage(client, settings.minio_bucket)


def get_object_storage() -> ObjectStorage:
    """DI provider. Returns the MinIO-backed storage; falls back to in-memory if
    the minio client/library is unavailable (so the app still boots)."""
    try:
        return _minio_storage()
    except Exception:  # noqa: BLE001 — never block app boot on storage init
        return InMemoryObjectStorage()
