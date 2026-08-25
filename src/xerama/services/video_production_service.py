"""Shot video-take production service (MODULE-032, formerly Module 08).

"Generate versioned video takes from approved keyframes and Director shot
contracts." Mirrors `StoryboardService`'s pattern: a lightweight per-shot
`ShotVideoProduction` workflow record plus plain `Asset` rows (type=video)
for every take - reusing `AssetService`'s accept/reject/take-numbering
machinery rather than building a parallel one.

Continuity groups (ADR-017 / research/PRODUCTION_STACK_2026.md "Previous-
frame continuity"): shots sharing a `continuity_group` must generate
sequentially - a shot after the first in its group requires its
immediate predecessor's take to be accepted *and* last-frame-extracted
first (`ContinuityOrderingError` otherwise), and that extracted frame -
not the original storyboard keyframe - becomes this shot's `first_frame`
input. Independent shots (no continuity_group, or the first shot in a
group) have no such ordering constraint and may generate concurrently.

Failed/rejected takes never invalidate or force regeneration of any other
shot's takes - there is no cascading invalidation here, unlike episode/
canon regeneration (Module 02).

`generate_lip_synced_take` (MODULE-036) reuses this same per-shot
production record and take-numbering rather than a fourth parallel
workflow table: a lip-synced clip is just another way to produce a video
take for a shot, so it lives here next to `generate_take`. Source video/
audio assets are read, never mutated - the synced result is always a new
take, and rejecting it never corrupts either source.
"""

from xerama.domain.asset import Asset, AssetOwnership, AssetProvenance, AssetType
from xerama.domain.enums import MediaQCDimension
from xerama.domain.generation_request import ShotGenerationRequest
from xerama.domain.scene import SceneBlocking
from xerama.domain.video_production import ShotVideoProduction
from xerama.providers.frame_extractor import FrameExtractor
from xerama.providers.lip_sync import LipSyncProvider, LipSyncRequest
from xerama.providers.media_qc import MediaQCContext
from xerama.providers.video import VideoGenerationRequest, VideoProvider, matches_requirements
from xerama.repositories.interfaces import VideoProductionRepository
from xerama.services.asset_service import AssetService
from xerama.services.media_qc_service import MediaQCService
from xerama.services.media_router import MediaProviderRouter


class ContinuityOrderingError(ValueError):
    """Raised when a shot in a continuity group is requested before its
    immediate predecessor has an accepted, last-frame-extracted take."""


class LipSyncEligibilityError(ValueError):
    """Raised when the target character isn't eligible for lip sync in
    this shot (per MODULE-022's structured `SceneBlocking`, when
    available) - "validate visible speaker" without needing real face
    detection: a character explicitly marked not-visible in the shot's
    blocking plan cannot be lip-synced."""


class VideoProductionService:
    def __init__(
        self,
        production_repo: VideoProductionRepository,
        asset_service: AssetService,
        frame_extractor: FrameExtractor,
        media_qc: MediaQCService,
    ) -> None:
        self._production_repo = production_repo
        self._asset_service = asset_service
        self._frame_extractor = frame_extractor
        self._media_qc = media_qc

    async def get_or_create_production(
        self,
        episode_id: str,
        scene_number: int,
        shot_number: int,
        continuity_group: str | None = None,
    ) -> ShotVideoProduction:
        return await self._production_repo.get_or_create(
            episode_id, scene_number, shot_number, continuity_group
        )

    async def get(self, production_id: str) -> ShotVideoProduction:
        production = await self._production_repo.get(production_id)
        if production is None:
            raise ValueError(f"video production {production_id} not found")
        return production

    async def list_by_episode(self, episode_id: str) -> list[ShotVideoProduction]:
        return await self._production_repo.list_by_episode(episode_id)

    async def generate_take(
        self,
        production_id: str,
        project_id: str,
        request: ShotGenerationRequest,
        video_router: MediaProviderRouter[VideoProvider],
        keyframe_bytes: bytes | None = None,
        series_id: str | None = None,
    ) -> Asset:
        production = await self.get(production_id)
        first_frame = keyframe_bytes

        if production.continuity_group:
            predecessor = await self._production_repo.get_previous_in_continuity_group(
                production.episode_id,
                production.continuity_group,
                production.scene_number,
                production.shot_number,
            )
            if predecessor is not None:
                if predecessor.extracted_last_frame_asset_id is None:
                    raise ContinuityOrderingError(
                        f"shot {predecessor.scene_number}.{predecessor.shot_number} "
                        f"(continuity_group={production.continuity_group!r}) must be generated, "
                        "accepted, and last-frame-extracted before this shot can generate"
                    )
                # The actual final frame of the previous shot is a better
                # continuity anchor than the original storyboard keyframe.
                first_frame = await self._asset_service.read_bytes(
                    predecessor.extracted_last_frame_asset_id
                )

        reference_ids = list(request.references.character_asset_ids)
        if request.references.style_asset_id:
            reference_ids.append(request.references.style_asset_id)
        if request.references.location_asset_id:
            reference_ids.append(request.references.location_asset_id)

        reference_images: list[bytes] = []
        for asset_id in reference_ids:
            asset = await self._asset_service.get(asset_id)
            if asset is None:
                continue
            reference_images.append(await self._asset_service.read_bytes(asset_id))

        def is_compatible(provider: VideoProvider) -> bool:
            return matches_requirements(
                provider.capabilities,
                request.provider_requirements,
                aspect_ratio=request.aspect_ratio,
                duration_seconds=request.duration_seconds,
            )

        async def call(provider: VideoProvider) -> bytes:
            return await provider.generate(
                VideoGenerationRequest(
                    prompt=request.prompt,
                    negative_prompt=request.negative_prompt,
                    aspect_ratio=request.aspect_ratio,
                    duration_seconds=request.duration_seconds,
                ),
                reference_images,
                first_frame=first_frame,
            )

        provider, data, attempts = await video_router.generate(is_compatible, call)

        take_number = await self._next_take_number(project_id, production)
        return await self._asset_service.ingest_bytes(
            data,
            AssetType.VIDEO,
            AssetOwnership(
                project_id=project_id,
                series_id=series_id,
                episode_id=production.episode_id,
                scene_number=production.scene_number,
                shot_number=production.shot_number,
            ),
            provenance=AssetProvenance(
                provider=provider.name,
                source_reference_asset_ids=reference_ids,
                generation_params={"routing_attempts": [a.model_dump() for a in attempts]},
            ),
            mime_type="video/mp4",
            ext=".mp4",
            duration_seconds=request.duration_seconds,
            take_number=take_number,
        )

    async def generate_lip_synced_take(
        self,
        production_id: str,
        project_id: str,
        source_video_asset_id: str,
        source_audio_asset_id: str,
        lip_sync_router: MediaProviderRouter[LipSyncProvider],
        duration_seconds: float,
        aspect_ratio: str = "9:16",
        character_id: str | None = None,
        blocking_plan: SceneBlocking | None = None,
        series_id: str | None = None,
    ) -> Asset:
        """Synchronize a controlled dialogue take (MODULE-034/035) onto a
        visible speaking character's video take (MODULE-036) - only when
        native audio is insufficient. `source_video_asset_id`/
        `source_audio_asset_id` are read, never mutated; the result is
        always a new take for this shot."""
        production = await self.get(production_id)
        self._validate_lip_sync_eligibility(character_id, blocking_plan)
        video_bytes = await self._asset_service.read_bytes(source_video_asset_id)
        audio_bytes = await self._asset_service.read_bytes(source_audio_asset_id)

        def is_compatible(provider: LipSyncProvider) -> bool:
            capabilities = provider.capabilities
            if aspect_ratio not in capabilities.supported_aspects:
                return False
            return duration_seconds <= capabilities.max_duration_seconds

        async def call(provider: LipSyncProvider) -> bytes:
            return await provider.sync(
                LipSyncRequest(aspect_ratio=aspect_ratio, duration_seconds=duration_seconds),
                video_bytes,
                audio_bytes,
            )

        provider, data, attempts = await lip_sync_router.generate(is_compatible, call)

        take_number = await self._next_take_number(project_id, production)
        return await self._asset_service.ingest_bytes(
            data,
            AssetType.VIDEO,
            AssetOwnership(
                project_id=project_id,
                series_id=series_id,
                episode_id=production.episode_id,
                scene_number=production.scene_number,
                shot_number=production.shot_number,
            ),
            provenance=AssetProvenance(
                provider=provider.name,
                source_reference_asset_ids=[source_video_asset_id, source_audio_asset_id],
                generation_params={
                    "lip_synced": True,
                    "routing_attempts": [a.model_dump() for a in attempts],
                },
            ),
            mime_type="video/mp4",
            ext=".mp4",
            duration_seconds=duration_seconds,
            take_number=take_number,
        )

    def _validate_lip_sync_eligibility(
        self, character_id: str | None, blocking_plan: SceneBlocking | None
    ) -> None:
        if character_id is None or blocking_plan is None:
            return  # nothing structured to validate against - permissive
        block = next(
            (cb for cb in blocking_plan.characters if cb.character_id == character_id), None
        )
        if block is not None and not block.visible:
            raise LipSyncEligibilityError(
                f"{character_id} is marked not visible in this shot's blocking plan - "
                "not eligible for lip sync"
            )

    async def upload_take(
        self,
        production_id: str,
        project_id: str,
        data: bytes,
        mime_type: str = "",
        ext: str = "",
        duration_seconds: float | None = None,
        series_id: str | None = None,
    ) -> Asset:
        """Manual upload fallback - first-class, same principle as every
        other media-ingest path in this codebase (Modules 04/06)."""
        production = await self.get(production_id)
        take_number = await self._next_take_number(project_id, production)
        return await self._asset_service.ingest_bytes(
            data,
            AssetType.VIDEO,
            AssetOwnership(
                project_id=project_id,
                series_id=series_id,
                episode_id=production.episode_id,
                scene_number=production.scene_number,
                shot_number=production.shot_number,
            ),
            provenance=AssetProvenance(provider="manual_upload"),
            mime_type=mime_type,
            ext=ext,
            duration_seconds=duration_seconds,
            take_number=take_number,
        )

    async def accept_take(
        self, production_id: str, asset_id: str, character_reference_ids: list[str] | None = None
    ) -> ShotVideoProduction:
        """MODULE-044 - a take cannot become accepted without passing its
        QC gate first: always MEDIA_HEALTH and MOTION; CONTINUITY
        additionally runs when this shot is mid a `continuity_group` with
        an already-accepted-and-extracted predecessor (checked against
        that predecessor's extracted last frame); IDENTITY when character
        reference assets are supplied. Raises `QCGateBlockedError` (never
        accepts) on a BLOCK verdict."""
        production = await self.get(production_id)
        dimensions = [MediaQCDimension.MEDIA_HEALTH, MediaQCDimension.MOTION]
        reference_ids = list(character_reference_ids or [])
        if production.continuity_group:
            predecessor = await self._production_repo.get_previous_in_continuity_group(
                production.episode_id,
                production.continuity_group,
                production.scene_number,
                production.shot_number,
            )
            if predecessor is not None and predecessor.extracted_last_frame_asset_id:
                reference_ids.append(predecessor.extracted_last_frame_asset_id)
                dimensions.append(MediaQCDimension.CONTINUITY)
        if character_reference_ids:
            dimensions.append(MediaQCDimension.IDENTITY)
        context = MediaQCContext(expected_aspect_ratio="9:16", reference_asset_ids=reference_ids)
        await self._media_qc.run_gate(asset_id, dimensions, context)

        asset = await self._asset_service.accept(asset_id)
        approved = await self._production_repo.approve(production_id, asset_id)
        if production.continuity_group:
            # Only extract when a later shot could actually depend on it -
            # standalone shots outside any continuity group never need this.
            video_bytes = await self._asset_service.read_bytes(asset.id)
            frame_bytes = await self._frame_extractor.extract_last_frame(video_bytes)
            frame_asset = await self._asset_service.ingest_bytes(
                frame_bytes,
                AssetType.IMAGE,
                AssetOwnership(
                    project_id=asset.ownership.project_id,
                    series_id=asset.ownership.series_id,
                    episode_id=production.episode_id,
                    scene_number=production.scene_number,
                    shot_number=production.shot_number,
                ),
                provenance=AssetProvenance(
                    provider="frame_extractor", source_reference_asset_ids=[asset.id]
                ),
                mime_type="image/png",
                ext=".png",
            )
            approved = await self._production_repo.set_extracted_last_frame(
                production_id, frame_asset.id
            )
        return approved

    async def reject_take(self, asset_id: str, reason: str) -> Asset:
        """Production stays in `draft` - the next `generate_take`/
        `upload_take` call is the retry. Never overwrites/deletes the
        rejected take (ADR-019)."""
        return await self._asset_service.reject(asset_id, reason)

    async def list_takes(self, project_id: str, production: ShotVideoProduction) -> list[Asset]:
        return await self._asset_service.list_by_ownership(
            project_id,
            episode_id=production.episode_id,
            scene_number=production.scene_number,
            shot_number=production.shot_number,
            asset_type=AssetType.VIDEO,
        )

    async def _next_take_number(self, project_id: str, production: ShotVideoProduction) -> int:
        existing = await self.list_takes(project_id, production)
        return max((a.take_number for a in existing), default=0) + 1
