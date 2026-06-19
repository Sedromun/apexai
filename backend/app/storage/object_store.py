"""Object storage abstraction for raw lap traces.

The :class:`ObjectStore` interface lets the service layer stay storage-agnostic:
production uses :class:`S3ObjectStore` (MinIO in dev, R2/Selectel/VK in prod), while
tests inject :class:`InMemoryObjectStore` — so no S3 service is needed to run the suite.

boto3 is synchronous; calls are offloaded to a worker thread via ``anyio.to_thread`` so
they never block the event loop. (S3 round-trips are infrequent — one put/get per lap.)
"""

from __future__ import annotations

import abc
from functools import lru_cache

import anyio
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.errors import NotFoundError


class ObjectStore(abc.ABC):
    @abc.abstractmethod
    async def ensure_ready(self) -> None:
        """Create the bucket if it does not yet exist (best-effort, dev convenience)."""

    @abc.abstractmethod
    async def put(self, key: str, data: bytes, *, content_type: str, content_encoding: str) -> None:
        ...

    @abc.abstractmethod
    async def get(self, key: str) -> bytes:
        """Return the object bytes, or raise :class:`NotFoundError` if it is missing."""


class S3ObjectStore(ObjectStore):
    def __init__(self) -> None:
        addressing = "path" if settings.s3_use_path_style else "auto"
        self._bucket = settings.s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": addressing}),
        )

    async def ensure_ready(self) -> None:
        await anyio.to_thread.run_sync(self._ensure_bucket_sync)

    def _ensure_bucket_sync(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)

    async def put(
        self, key: str, data: bytes, *, content_type: str, content_encoding: str
    ) -> None:
        await anyio.to_thread.run_sync(
            lambda: self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                ContentEncoding=content_encoding,
            )
        )

    async def get(self, key: str) -> bytes:
        return await anyio.to_thread.run_sync(self._get_sync, key)

    def _get_sync(self, key: str) -> bytes:
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in {"NoSuchKey", "404", "NoSuchBucket"}:
                raise NotFoundError("Trace object not found", code="trace_not_found") from exc
            raise
        return resp["Body"].read()


class InMemoryObjectStore(ObjectStore):
    """Process-local store for tests and offline development."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def ensure_ready(self) -> None:
        return None

    async def put(
        self, key: str, data: bytes, *, content_type: str, content_encoding: str
    ) -> None:
        self._objects[key] = data

    async def get(self, key: str) -> bytes:
        if key not in self._objects:
            raise NotFoundError("Trace object not found", code="trace_not_found")
        return self._objects[key]


@lru_cache
def get_object_store() -> ObjectStore:
    """FastAPI dependency: process-wide singleton S3 store (overridden in tests)."""
    return S3ObjectStore()
