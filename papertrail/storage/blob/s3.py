"""S3 blob storage — stub for post-v1."""

from __future__ import annotations


class S3BlobStore:
    """Placeholder for S3 blob storage. Not implemented in v1."""

    async def put(self, key: str, data: bytes) -> str:
        raise NotImplementedError("S3 storage is not available in v1")

    async def get(self, uri: str) -> bytes:
        raise NotImplementedError("S3 storage is not available in v1")

    async def delete(self, uri: str) -> None:
        raise NotImplementedError("S3 storage is not available in v1")
