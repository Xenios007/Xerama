"""Storyboard/keyframe workflow service (Module 06, provider selection
generalized in Module 07).

"approved shot -> rough storyboard/layout -> compiled references -> final
keyframe -> QC state -> accept/retry." The caller compiles the
`ShotGenerationRequest` (Module 03's `PromptCompiler`, now consulting
Module 05's `ConsistencyPolicy` and Module 06's Style Bible) and hands it
in; this service resolves those reference ids to actual bytes, asks the
`MediaProviderRouter` for a capability-eligible, healthy provider (falling
back across registered image providers on failure - Module 07), and
persists the result as a durable `Asset` via `AssetService` (Module 04) -
never a new media-storage mechanism of its own.
"""

from xerama.domain.asset import Asset, AssetOwnership, AssetProvenance, AssetType
from xerama.domain.enums import MediaQCDimension, RepairAction
from xerama.domain.generation_request import ShotGenerationRequest
from xerama.domain.storyboard import Storyboard
from xerama.providers.image import ImageEditRequest, ImageGenerationRequest, ImageProvider
from xerama.providers.media_qc import MediaQCContext
from xerama.repositories.interfaces import StoryboardRepository
from xerama.services.asset_service import AssetService
from xerama.services.media_qc_service import MediaQCService, QCGateBlockedError
from xerama.services.media_router import MediaProviderRouter
from xerama.services.retake_service import AutomaticRetakeService


class StoryboardService:
    def __init__(
        self,
        storyboard_repo: StoryboardRepository,
        asset_service: AssetService,
        media_qc: MediaQCService,
    ) -> None:
        self._storyboard_repo = storyboard_repo
        self._asset_service = asset_service
        self._media_qc = media_qc

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
        image_router: MediaProviderRouter[ImageProvider],
        series_id: str | None = None,
        excluded_providers: set[str] | None = None,
        min_reference_images: int | None = None,
    ) -> Asset:
        """`excluded_providers`/`min_reference_images` are MODULE-045
        auto-heal levers (ALTERNATE_PROVIDER / STRONGER_REFERENCES) - both
        default to "no restriction" so ordinary callers are unaffected."""
        storyboard = await self.get(storyboard_id)
        excluded_providers = excluded_providers or set()

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
        wants_references = bool(reference_images)

        def is_compatible(provider: ImageProvider) -> bool:
            if provider.name in excluded_providers:
                return False
            capabilities = provider.capabilities
            if request.aspect_ratio not in capabilities.supported_aspects:
                return False
            if min_reference_images is not None and capabilities.max_reference_images < min_reference_images:
                return False
            return not (wants_references and not capabilities.supports_reference_images)

        async def call(provider: ImageProvider) -> bytes:
            bounded = reference_images[: provider.capabilities.max_reference_images]
            return await provider.generate(
                ImageGenerationRequest(
                    prompt=request.prompt,
                    negative_prompt=request.negative_prompt,
                    aspect_ratio=request.aspect_ratio,
                ),
                bounded,
            )

        provider, data, attempts = await image_router.generate(is_compatible, call)

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
                provider=provider.name,
                source_reference_asset_ids=reference_ids,
                generation_params={"routing_attempts": [a.model_dump() for a in attempts]},
            ),
            mime_type="image/png",
            ext=".png",
            take_number=take_number,
        )

    async def edit_keyframe(
        self,
        storyboard_id: str,
        project_id: str,
        instruction: str,
        base_asset_id: str,
        image_router: MediaProviderRouter[ImageProvider],
        mask_asset_id: str | None = None,
        negative_prompt: str = "",
        aspect_ratio: str = "9:16",
        series_id: str | None = None,
    ) -> Asset:
        """Targeted repair of one existing take (MODULE-030) - only routes
        to providers whose `capabilities.supports_edit` is `True`, never
        touches `base_asset_id` itself (always produces a new take, so an
        accepted take is never silently overwritten), and preserves full
        lineage (`source_reference_asset_ids` records what this edit was
        based on)."""
        storyboard = await self.get(storyboard_id)
        base_image = await self._asset_service.read_bytes(base_asset_id)
        mask = await self._asset_service.read_bytes(mask_asset_id) if mask_asset_id else None

        def is_compatible(provider: ImageProvider) -> bool:
            capabilities = provider.capabilities
            if not capabilities.supports_edit:
                return False
            if mask is not None and not capabilities.supports_mask:
                return False
            return aspect_ratio in capabilities.supported_aspects

        async def call(provider: ImageProvider) -> bytes:
            return await provider.edit(
                ImageEditRequest(
                    instruction=instruction, negative_prompt=negative_prompt, aspect_ratio=aspect_ratio
                ),
                base_image,
                mask,
            )

        provider, data, attempts = await image_router.generate(is_compatible, call)

        reference_ids = [base_asset_id] + ([mask_asset_id] if mask_asset_id else [])
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
                provider=provider.name,
                source_reference_asset_ids=reference_ids,
                generation_params={
                    "edit": True,
                    "based_on_take": base_asset_id,
                    "routing_attempts": [a.model_dump() for a in attempts],
                },
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

    async def accept_keyframe(
        self,
        storyboard_id: str,
        asset_id: str,
        style_dna: str = "",
        character_reference_ids: list[str] | None = None,
    ) -> Storyboard:
        """MODULE-044 - a keyframe cannot become accepted without passing
        its QC gate first: always MEDIA_HEALTH (file integrity) and
        COMPOSITION (9:16 framing); STYLE/IDENTITY additionally run when
        the caller has style DNA / character reference assets to check
        against. Raises `QCGateBlockedError` (never accepts) on a BLOCK
        verdict."""
        dimensions = [MediaQCDimension.MEDIA_HEALTH, MediaQCDimension.COMPOSITION]
        reference_ids = list(character_reference_ids or [])
        if style_dna:
            dimensions.append(MediaQCDimension.STYLE)
        if reference_ids:
            dimensions.append(MediaQCDimension.IDENTITY)
        context = MediaQCContext(
            expected_aspect_ratio="9:16", style_dna=style_dna, reference_asset_ids=reference_ids
        )
        await self._media_qc.run_gate(asset_id, dimensions, context)
        await self._asset_service.accept(asset_id)
        return await self._storyboard_repo.approve(storyboard_id, asset_id)

    async def reject_keyframe(self, asset_id: str, reason: str) -> Asset:
        """Storyboard stays in `draft` - the next `generate_keyframe`/
        `upload_keyframe` call is the retry."""
        return await self._asset_service.reject(asset_id, reason)

    async def generate_with_auto_heal(
        self,
        storyboard_id: str,
        project_id: str,
        request: ShotGenerationRequest,
        image_router: MediaProviderRouter[ImageProvider],
        retake_service: AutomaticRetakeService,
        series_id: str | None = None,
        style_dna: str = "",
        character_reference_ids: list[str] | None = None,
    ) -> tuple[Asset, Storyboard]:
        """MODULE-045 - generate, QC-gate, and automatically repair-and-
        retry a keyframe up to `AutomaticRetakeService`'s attempt budget.
        Every failed take is preserved and explicitly rejected with its QC
        reasons (ADR-019 - never silently abandoned). Returns the accepted
        asset + storyboard once QC passes, or re-raises
        `QCGateBlockedError` once the budget is exhausted - the storyboard
        is marked `escalated` for human review at that point."""
        excluded_providers: set[str] = set()
        min_reference_images: int | None = None
        current_request = request
        while True:
            asset = await self.generate_keyframe(
                storyboard_id,
                project_id,
                current_request,
                image_router,
                series_id=series_id,
                excluded_providers=excluded_providers,
                min_reference_images=min_reference_images,
            )
            try:
                approved = await self.accept_keyframe(
                    storyboard_id,
                    asset.id,
                    style_dna=style_dna,
                    character_reference_ids=character_reference_ids,
                )
                return asset, approved
            except QCGateBlockedError as exc:
                storyboard = await self.get(storyboard_id)
                plan = retake_service.plan_repair(exc.attempts, storyboard.auto_retake_attempts)
                await self._storyboard_repo.record_retake_attempt(
                    storyboard_id, escalated=(plan.action == RepairAction.ESCALATE)
                )
                await self.reject_keyframe(
                    asset.id, f"MODULE-045 auto-heal ({plan.action.value}): {'; '.join(plan.reasons)}"
                )
                if plan.action == RepairAction.ESCALATE:
                    raise
                if plan.action == RepairAction.STRONGER_REFERENCES:
                    min_reference_images = len(
                        current_request.references.character_asset_ids
                    ) + bool(current_request.references.style_asset_id) + bool(
                        current_request.references.location_asset_id
                    )
                elif plan.action == RepairAction.PROMPT_REPAIR:
                    suffix = "; ".join(plan.reasons)
                    current_request = current_request.model_copy(
                        update={
                            "negative_prompt": (current_request.negative_prompt + f"; avoid: {suffix}").strip(
                                "; "
                            )
                        }
                    )
                elif plan.action == RepairAction.ALTERNATE_PROVIDER:
                    excluded_providers.add(asset.provenance.provider)
                # FULL_RETAKE: no adjustment, just try again.

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
