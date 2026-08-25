"""Multimodal QC coordination service (MODULE-044).

The one place that runs a QC dimension check (deterministic or
vision-provider-backed), persists the attempt, and gates acceptance.
`StoryboardService.accept_keyframe` / `VideoProductionService.accept_take`
/ `AudioProductionService.accept_take` all call `run_gate` before flipping
an asset to ACCEPTED - "Production assets cannot become accepted/
publishable without defined QC gates" (MODULE-044 "Done when").
"""

from xerama.domain.enums import MediaQCDimension, QCStatus
from xerama.domain.media_qc import MediaQCAttempt
from xerama.pipeline.media_qc_checks import check_dialogue_audio, check_media_health
from xerama.providers.media_qc import MediaQCContext, MediaQCProvider
from xerama.repositories.interfaces import MediaQCRepository
from xerama.services.asset_service import AssetService

DETERMINISTIC_DIMENSIONS = frozenset({MediaQCDimension.MEDIA_HEALTH, MediaQCDimension.DIALOGUE_AUDIO})


class QCGateBlockedError(ValueError):
    """A QC gate returned BLOCK for at least one dimension - the asset
    stays not-accepted. Carries every attempt run in this gate pass so the
    caller/API can surface exactly why."""

    def __init__(self, asset_id: str, attempts: list[MediaQCAttempt]) -> None:
        blocked = [a for a in attempts if a.status == QCStatus.BLOCK]
        reasons = [r for a in blocked for r in a.reasons] or [
            f"{a.dimension.value} gate blocked" for a in blocked
        ]
        super().__init__(f"asset {asset_id} failed QC gate ({'; '.join(reasons)})")
        self.asset_id = asset_id
        self.attempts = attempts


class MediaQCService:
    def __init__(
        self, repo: MediaQCRepository, asset_service: AssetService, provider: MediaQCProvider
    ) -> None:
        self._repo = repo
        self._asset_service = asset_service
        self._provider = provider

    async def run_check(
        self, asset_id: str, dimension: MediaQCDimension, context: MediaQCContext | None = None
    ) -> MediaQCAttempt:
        asset = await self._asset_service.get(asset_id)
        if asset is None:
            raise ValueError(f"asset {asset_id} not found")
        context = context or MediaQCContext()

        if dimension == MediaQCDimension.MEDIA_HEALTH:
            result = check_media_health(
                asset, context.expected_duration_seconds, context.expected_aspect_ratio
            )
        elif dimension == MediaQCDimension.DIALOGUE_AUDIO:
            result = check_dialogue_audio(asset, context.expected_duration_seconds)
        else:
            candidate_bytes = await self._asset_service.read_bytes(asset_id)
            reference_bytes: list[bytes] = []
            for reference_id in context.reference_asset_ids:
                reference_asset = await self._asset_service.get(reference_id)
                if reference_asset is None:
                    # No real reference asset exists yet (e.g. a pre-image
                    # identity fallback) - skip rather than fail, same
                    # precedent as StoryboardService.generate_keyframe.
                    continue
                reference_bytes.append(await self._asset_service.read_bytes(reference_id))
            result = await self._provider.score(
                dimension, asset, candidate_bytes, reference_bytes, context
            )

        evidence = {
            "asset_type": asset.type.value,
            "size_bytes": asset.size_bytes,
            "width": asset.width,
            "height": asset.height,
            "duration_seconds": asset.duration_seconds,
            "expected_duration_seconds": context.expected_duration_seconds,
            "expected_aspect_ratio": context.expected_aspect_ratio,
            "reference_asset_ids": context.reference_asset_ids,
        }
        return await self._repo.create(
            asset_id=asset_id,
            dimension=dimension,
            status=result.status,
            score=result.score,
            evidence=evidence,
            reasons=result.reasons,
            repair_recommendation=result.repair_recommendation,
        )

    async def run_gate(
        self,
        asset_id: str,
        dimensions: list[MediaQCDimension],
        context: MediaQCContext | None = None,
    ) -> list[MediaQCAttempt]:
        """Runs every given dimension and raises `QCGateBlockedError` if
        any comes back BLOCK. Callers (an accept_* method) must call this
        *before* flipping the asset to ACCEPTED, never after."""
        attempts = [await self.run_check(asset_id, dimension, context) for dimension in dimensions]
        if any(a.status == QCStatus.BLOCK for a in attempts):
            raise QCGateBlockedError(asset_id, attempts)
        return attempts

    async def list_attempts(self, asset_id: str) -> list[MediaQCAttempt]:
        return await self._repo.list_by_asset(asset_id)
