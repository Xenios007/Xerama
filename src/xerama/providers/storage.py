"""Storage provider contract (Module 04). See ADR-022 - local first, an
S3-compatible adapter can implement the same Protocol later without
touching `AssetService` or repository code.
"""

from pathlib import Path
from typing import Protocol


class StorageProvider(Protocol):
    """All paths are relative to the provider's root; callers never see or
    construct absolute filesystem paths."""

    async def save_bytes(self, data: bytes, relative_path: str) -> str:
        """Writes `data` at `relative_path` (creating parent dirs) and
        returns the (possibly normalized) relative path actually used."""
        ...

    async def save_file(self, source_path: str, relative_path: str) -> str: ...

    async def read_bytes(self, relative_path: str) -> bytes: ...

    async def exists(self, relative_path: str) -> bool: ...

    async def delete(self, relative_path: str) -> None: ...

    async def list_all(self) -> list[str]:
        """All relative paths currently stored - used for orphan scans."""
        ...

    def absolute_path(self, relative_path: str) -> Path: ...
