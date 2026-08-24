"""Storyboard/keyframe workflow service (Module 06).

"approved shot -> rough storyboard/layout -> compiled references -> final
keyframe -> QC state -> accept/retry." The caller compiles the
`ShotGenerationRequest` (Module 03's `PromptCompiler`, now consulting
Module 05's `ConsistencyPolicy` and this module's Style Bible) and hands it
in; this service resolves those reference ids to actual bytes, rejects an
incompatible provider before spending a generation request (see
research/PRODUCTION_STACK_2026.md "Provider contract"), and persists the
result as a durable `Asset` via `AssetService` (Module 04) - never a new
media-storage mechanism of its own.
"""

from xerama.domain.asset import Asset, AssetOwnership, AssetProvenance, AssetType
from xerama.domain.generation_request import ShotGenerationRequest
from xerama.domain.storyboard import Storyboard
from xerama.providers.image import ImageGenerationRequest, ImageProvider
from xerama.repositories.interfaces import StoryboardRepository
from xerama.services.asset_service import AssetService


class UnsupportedProviderCapabilityError(ValueError):
    """Raised when a request needs something the chosen `ImageProvider`
    cannot do - before any generation call is made."""


class StoryboardService:
    def __init__(self, storyboard_repo: StoryboardRepository, asset_service: AssetService) -> None:
        self._storyboard_repo = storyboard_repo
        self._asset_service = asset_service

    async def get_or_create_storyboard(
        self, episode_id: str, scene_number: int, shot_number: int, layout_description: str = ""
    ) -> Storyboard:
        return await self._storyboard_repo.get_or_create(
            episode_id, scene_number, shot_number, layout_description
        )

    async def get(self, storyboard_id: str) -> Storyboard:
        storyboard = await self._storyboard_repo.get(storyboard_id)
        if storyboard is None:
            raise ValueError(f"storyboard {storyboard_id} not found")
        return storyboard

    async def list_by_episode(self, episode_id: str) -> list[Storyboard]:
        return await self._storyboard_repo.list_by_episode(episode_id)

    async def generate_keyframe(
        self,
        storyboard_id: str,
        project_id: str,
        request: ShotGenerationRequest,
        image_provider: ImageProvider,
        series_id: str | None = None,
    ) -> Asset:
        storyboard = await self.get(storyboard_id)
        self._reject_if_incompatible(image_provider, request)

        reference_ids = list(request.references.character_asset_ids)
        if request.references.style_asset_id:
            reference_ids.append(request.references.style_asset_id)
        if request.references.location_asset_id:
            reference_ids.append(request.references.location_asset_id)

        reference_images: list[bytes] = []
        for asset_id in reference_ids:
            asset = await self._asset_service.get(asset_id)
            if asset is None:
                # No real image exists yet for this reference (e.g.
                # pre-image-generation Character DNA fallback) - skip rather
                # than fail; the prompt/DNA text still carries the identity.
                continue
            reference_images.append(await self._asset_service.read_bytes(asset_id))
        reference_images = reference_images[: image_provider.capabilities.max_reference_images]

        data = await image_provider.generate(
            ImageGenerationRequest(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                aspect_ratio=request.aspect_ratio,
            ),
            reference_images,
        )

        take_number = await self._next_take_number(project_id, storyboard)
        return await self._asset_service.ingest_bytes(
            data,
            AssetType.IMAGE,
            AssetOwnership(
                project_id=project_id,
                series_id=series_id,
                episode_id=storyboard.episode_id,
                scene_number=storyboard.scene_number,
                shot_number=storyboard.shot_number,
            ),
            provenance=AssetProvenance(
                provider=image_provider.name, source_reference_asset_ids=reference_ids
            ),
            mime_type="image/png",
            ext=".png",
            take_number=take_number,
        )

    async def upload_keyframe(
        self,
        storyboard_id: str,
        project_id: str,
        data: bytes,
        mime_type: str = "",
        ext: str = "",
        series_id: str | None = None,
    ) -> Asset:
        """Manual upload fallback - first-class, not a degraded path (same
        principle as Module 04/06's manual-upload requirement)."""
        storyboard = await self.get(storyboard_id)
        take_number = await self._next_take_number(project_id, storyboard)
        return await self._asset_service.ingest_bytes(
            data,
            AssetType.IMAGE,
            AssetOwnership(
                project_id=project_id,
                series_id=series_id,
                episode_id=storyboard.episode_id,
                scene_number=storyboard.scene_number,
                shot_number=storyboard.shot_number,
            ),
            provenance=AssetProvenance(provider="manual_upload"),
            mime_type=mime_type,
            ext=ext,
            take_number=take_number,
        )

    async def accept_keyframe(self, storyboard_id: str, asset_id: str) -> Storyboard:
        await self._asset_service.accept(asset_id)
        return await self._storyboard_repo.approve(storyboard_id, asset_id)

    async def reject_keyframe(self, asset_id: str, reason: str) -> Asset:
        """Storyboard stays in `draft` - the next `generate_keyframe`/
        `upload_keyframe` call is the retry."""
        return await self._asset_service.reject(asset_id, reason)

    async def list_keyframes(self, project_id: str, storyboard: Storyboard) -> list[Asset]:
        return await self._asset_service.list_by_ownership(
            project_id,
            episode_id=storyboard.episode_id,
            scene_number=storyboard.scene_number,
            shot_number=storyboard.shot_number,
            asset_type=AssetType.IMAGE,
        )

    async def _next_take_number(self, project_id: str, storyboard: Storyboard) -> int:
        existing = await self.list_keyframes(project_id, storyboard)
        return max((a.take_number for a in existing), default=0) + 1

    def _reject_if_incompatible(
        self, image_provider: ImageProvider, request: ShotGenerationRequest
    ) -> None:
        capabilities = image_provider.capabilities
        if request.aspect_ratio not in capabilities.supported_aspects:
            raise UnsupportedProviderCapabilityError(
                f"{image_provider.name} does not support aspect ratio {request.aspect_ratio!r} "
                f"(supports {capabilities.supported_aspects})"
            )
        wants_references = bool(
            request.references.character_asset_ids
            or request.references.style_asset_id
            or request.references.location_asset_id
        )
        if wants_references and not capabilities.supports_reference_images:
            raise UnsupportedProviderCapabilityError(
                f"{image_provider.name} does not support reference images"
            )
