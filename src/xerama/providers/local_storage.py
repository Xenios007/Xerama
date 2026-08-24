"""Local filesystem `StorageProvider` - Trial 01's asset store. See ADR-022.

Never store large media blobs in SQLite - this writes to plain files under
a configured root (`Settings.asset_storage_path`) and the database only
keeps the relative path + metadata.
"""

import asyncio
from pathlib import Path


class UnsafeStoragePathError(ValueError):
    """Raised when a relative path would resolve outside the storage root
    (path traversal via `..`, an absolute path, etc.)."""


class LocalStorageProvider:
    """Implements the `StorageProvider` Protocol (`providers/storage.py`)."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, relative_path: str) -> Path:
        candidate = (self._root / relative_path).resolve()
        try:
            candidate.relative_to(self._root)
        except ValueError as exc:
            raise UnsafeStoragePathError(
                f"storage path escapes root: {relative_path!r}"
            ) from exc
        return candidate

    async def save_bytes(self, data: bytes, relative_path: str) -> str:
        path = self._safe_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)
        return relative_path

    async def save_file(self, source_path: str, relative_path: str) -> str:
        data = await asyncio.to_thread(Path(source_path).read_bytes)
        return await self.save_bytes(data, relative_path)

    async def read_bytes(self, relative_path: str) -> bytes:
        path = self._safe_path(relative_path)
        if not path.is_file():
            raise FileNotFoundError(relative_path)
        return await asyncio.to_thread(path.read_bytes)

    async def exists(self, relative_path: str) -> bool:
        try:
            return self._safe_path(relative_path).is_file()
        except UnsafeStoragePathError:
            return False

    async def delete(self, relative_path: str) -> None:
        path = self._safe_path(relative_path)
        if path.is_file():
            await asyncio.to_thread(path.unlink)

    async def list_all(self) -> list[str]:
        def _walk() -> list[str]:
            return [
                str(p.relative_to(self._root)).replace("\\", "/")
                for p in self._root.rglob("*")
                if p.is_file()
            ]

        return await asyncio.to_thread(_walk)

    def absolute_path(self, relative_path: str) -> Path:
        return self._safe_path(relative_path)
