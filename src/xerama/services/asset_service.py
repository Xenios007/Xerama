"""Asset ingest/accept/reject/delete service (Module 04).

The single surface every current and future provider (image/video/voice/
lip-sync/editor) should use to turn raw output into a durable Xerama asset.
Combines content hashing, a `StorageProvider`, and an `AssetRepository` -
see ADR-020 (never treat a provider URL as permanent storage) and ADR-022
(local storage first).
"""

import asyncio
import hashlib
from pathlib import Path

import httpx

from xerama.domain.asset import Asset, AssetOwnership, AssetProvenance, AssetStatus, AssetType
from xerama.providers.storage import StorageProvider
from xerama.repositories.interfaces import AssetRepository


class AssetService:
    def __init__(self, storage: StorageProvider, asset_repo: AssetRepository) -> None:
        self._storage = storage
        self._asset_repo = asset_repo

    async def ingest_bytes(
        self,
        data: bytes,
        asset_type: AssetType,
        ownership: AssetOwnership,
        provenance: AssetProvenance | None = None,
        mime_type: str = "",
        ext: str = "",
        take_number: int = 1,
    ) -> Asset:
        content_hash = hashlib.sha256(data).hexdigest()
        relative_path = f"{content_hash[:2]}/{content_hash}{ext}"
        # Content-addressed: identical bytes already on disk are never
        # rewritten, giving free deduplication across the whole store.
        if not await self._storage.exists(relative_path):
            await self._storage.save_bytes(data, relative_path)
        return await self._asset_repo.create(
            asset_type=asset_type,
            storage_path=relative_path,
            content_hash=content_hash,
            ownership=ownership,
            provenance=provenance,
            mime_type=mime_type,
            size_bytes=len(data),
            take_number=take_number,
        )

    async def ingest_file(
        self,
        source_path: str,
        asset_type: AssetType,
        ownership: AssetOwnership,
        provenance: AssetProvenance | None = None,
        mime_type: str = "",
        ext: str = "",
        take_number: int = 1,
    ) -> Asset:
        data = await asyncio.to_thread(Path(source_path).read_bytes)
        return await self.ingest_bytes(
            data, asset_type, ownership, provenance, mime_type, ext, take_number
        )

    async def ingest_from_url(
        self,
        url: str,
        http_client: httpx.AsyncClient,
        asset_type: AssetType,
        ownership: AssetOwnership,
        provenance: AssetProvenance | None = None,
        ext: str = "",
        take_number: int = 1,
    ) -> Asset:
        """Downloads a (typically temporary) provider URL and immediately
        persists it - see ADR-020, "never treat provider URLs as permanent"."""
        response = await http_client.get(url)
        response.raise_for_status()
        provenance = (provenance or AssetProvenance()).model_copy(update={"source_url": url})
        mime_type = response.headers.get("content-type", "")
        return await self.ingest_bytes(
            response.content, asset_type, ownership, provenance, mime_type, ext, take_number
        )

    async def get(self, asset_id: str) -> Asset | None:
        return await self._asset_repo.get(asset_id)

    async def list_by_ownership(
        self,
        project_id: str,
        series_id: str | None = None,
        episode_id: str | None = None,
        character_id: str | None = None,
        scene_number: int | None = None,
        shot_number: int | None = None,
        asset_type: AssetType | None = None,
    ) -> list[Asset]:
        return await self._asset_repo.list_by_ownership(
            project_id,
            series_id=series_id,
            episode_id=episode_id,
            character_id=character_id,
            scene_number=scene_number,
            shot_number=shot_number,
            asset_type=asset_type,
        )

    async def accept(self, asset_id: str) -> Asset:
        return await self._asset_repo.set_status(asset_id, AssetStatus.ACCEPTED)

    async def reject(self, asset_id: str, reason: str) -> Asset:
        return await self._asset_repo.set_status(asset_id, AssetStatus.REJECTED, rejection_reason=reason)

    async def read_bytes(self, asset_id: str) -> bytes:
        asset = await self._asset_repo.get(asset_id)
        if asset is None:
            raise ValueError(f"asset {asset_id} not found")
        return await self._storage.read_bytes(asset.storage_path)

    async def delete(self, asset_id: str, force: bool = False) -> None:
        """Deletion policy: an ACCEPTED asset is protected unless `force`.
        The backing file is only removed once no other asset row (from
        content-hash dedup) still points at the same storage_path."""
        asset = await self._asset_repo.get(asset_id)
        if asset is None:
            return
        if asset.status == AssetStatus.ACCEPTED and not force:
            raise PermissionError(f"asset {asset_id} is accepted - pass force=True to delete it anyway")
        still_referenced = any(
            other.storage_path == asset.storage_path and other.id != asset_id
            for other in await self._asset_repo.list_all()
        )
        if not still_referenced:
            await self._storage.delete(asset.storage_path)
        await self._asset_repo.delete(asset_id)

    async def find_missing_files(self) -> list[Asset]:
        """Asset rows whose backing file is missing on disk - an integrity
        problem, not a normal orphan."""
        return [
            asset
            for asset in await self._asset_repo.list_all()
            if not await self._storage.exists(asset.storage_path)
        ]

    async def find_unreferenced_files(self) -> list[str]:
        """Files on disk with no asset row pointing at them - safe to purge."""
        referenced = {asset.storage_path for asset in await self._asset_repo.list_all()}
        return [path for path in await self._storage.list_all() if path not in referenced]
