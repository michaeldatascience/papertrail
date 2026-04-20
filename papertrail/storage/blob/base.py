"""Blob storage protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class BlobStore(Protocol):
    async def put(self, key: str, data: bytes) -> str:
        """Store data and return URI."""
        ...

    async def get(self, uri: str) -> bytes:
        """Retrieve data by URI."""
        ...

    async def delete(self, uri: str) -> None:
        """Delete data by URI."""
        ...
