"""Local filesystem blob storage."""

from __future__ import annotations

from pathlib import Path

from papertrail.config.loader import get_settings


class LocalBlobStore:
    def __init__(self, base_path: str | None = None):
        self._base = Path(base_path or get_settings().blob_storage_path)
        self._base.mkdir(parents=True, exist_ok=True)

    async def put(self, key: str, data: bytes) -> str:
        path = self._base / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"local://{path}"

    async def get(self, uri: str) -> bytes:
        path_str = uri.replace("local://", "")
        path = Path(path_str)
        if not path.exists():
            raise FileNotFoundError(f"Blob not found: {uri}")
        return path.read_bytes()

    async def delete(self, uri: str) -> None:
        path_str = uri.replace("local://", "")
        path = Path(path_str)
        if path.exists():
            path.unlink()
