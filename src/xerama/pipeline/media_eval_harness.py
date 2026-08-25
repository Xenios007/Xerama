"""Media evaluation harness (MODULE-073).

Runs a curated `MediaEvalCase` (eval/media_datasets.py) through the
*real* `MediaProviderRouter` for image or video generation - "live eval
opt-in": nothing here runs on its own, a caller decides when
(`FakeImageProvider`/`FakeVideoProvider` in every test, a real provider
only via an explicit API call). QC scoring reuses the exact
`MediaQCProvider` contract MODULE-044 already built (never a second
scoring system), and the generated asset is persisted through the real
`AssetService` so a benchmark run leaves the same durable, provenance-
tracked record any production generation would (ADR-020).
"""

import time

from xerama.domain.asset import AssetOwnership, AssetProvenance, AssetType
from xerama.domain.enums import QCStatus
from xerama.domain.media_eval import MediaEvalRunResult, MediaQCDimensionResult
from xerama.eval.media_datasets import SHOT_CLASS_QC_DIMENSIONS, MediaEvalCase
from xerama.providers.errors import ProviderError
from xerama.providers.image import ImageGenerationRequest
from xerama.providers.media_qc import MediaQCContext, MediaQCProvider
from xerama.providers.video import VideoGenerationRequest
from xerama.services.asset_service import AssetService
from xerama.services.media_router import MediaProviderRouter, NoEligibleProviderError

# A benchmark run has no real project - assets it produces are tagged
# with this fixed, non-FK-constrained ownership id (see db/models.py's
# Asset.project_id - a plain indexed String, never a foreign key) so
# they're inspectable/cleanable as a group without needing a real
# Project row.
EVAL_PROJECT_ID = "eval-bench"

_PLACEHOLDER_REFERENCE_BYTES = b"eval-harness placeholder reference image"


class MediaEvalHarness:
    def __init__(
        self,
        image_router: MediaProviderRouter,
        video_router: MediaProviderRouter,
        media_qc_provider: MediaQCProvider,
        asset_service: AssetService,
    ) -> None:
        self._image_router = image_router
        self._video_router = video_router
        self._media_qc_provider = media_qc_provider
        self._asset_service = asset_service

    async def run_case(self, case: MediaEvalCase, dataset_version: str) -> MediaEvalRunResult:
        reference_images = [_PLACEHOLDER_REFERENCE_BYTES for _ in range(case.reference_image_count)]
        started = time.perf_counter()

        try:
            provider, data, attempts = await self._generate(case, reference_images)
        except NoEligibleProviderError as exc:
            return MediaEvalRunResult(
                id="",
                case_id=case.id,
                shot_class=case.shot_class,
                asset_type=case.asset_type,
                dataset_version=dataset_version,
                provider="",
                generation_succeeded=False,
                attempts=len(exc.attempts),
                latency_ms=(time.perf_counter() - started) * 1000,
                error=str(exc),
            )

        latency_ms = (time.perf_counter() - started) * 1000
        asset = await self._asset_service.ingest_bytes(
            data,
            case.asset_type,
            AssetOwnership(project_id=EVAL_PROJECT_ID),
            provenance=AssetProvenance(provider=provider.name),
            mime_type="image/png" if case.asset_type == AssetType.IMAGE else "video/mp4",
        )

        qc_results = []
        for dimension in SHOT_CLASS_QC_DIMENSIONS.get(case.shot_class, ()):
            try:
                qc_result = await self._media_qc_provider.score(
                    dimension,
                    asset,
                    data,
                    reference_images,
                    MediaQCContext(shot_description=case.prompt),
                )
            except ProviderError:
                # A QC provider failure must not crash the whole
                # benchmark run - the same "expected failures degrade
                # safely" bar MODULE-070 set for the rest of the API. A
                # dimension that couldn't be scored counts as not-passed
                # for acceptance purposes below, never silently ignored.
                qc_results.append(
                    MediaQCDimensionResult(dimension=dimension.value, status="error", score=0.0)
                )
                continue
            qc_results.append(
                MediaQCDimensionResult(
                    dimension=dimension.value, status=qc_result.status.value, score=qc_result.score
                )
            )

        accepted = bool(qc_results) and all(r.status == QCStatus.PASS.value for r in qc_results)

        return MediaEvalRunResult(
            id="",
            case_id=case.id,
            shot_class=case.shot_class,
            asset_type=case.asset_type,
            dataset_version=dataset_version,
            provider=provider.name,
            generation_succeeded=True,
            attempts=attempts,
            latency_ms=latency_ms,
            estimated_cost_usd=provider.capabilities.estimated_cost_usd * attempts,
            qc_results=qc_results,
            accepted=accepted,
            asset_id=asset.id,
        )

    async def _generate(self, case: MediaEvalCase, reference_images: list[bytes]):
        attempts_made = 0

        async def _call(provider):
            nonlocal attempts_made
            attempts_made += 1
            if case.asset_type == AssetType.IMAGE:
                request = ImageGenerationRequest(prompt=case.prompt, negative_prompt=case.negative_prompt)
                return await provider.generate(request, reference_images)
            request = VideoGenerationRequest(
                prompt=case.prompt,
                negative_prompt=case.negative_prompt,
                duration_seconds=case.duration_seconds,
            )
            return await provider.generate(request, reference_images)

        router = self._image_router if case.asset_type == AssetType.IMAGE else self._video_router
        provider, data, _attempts_log = await router.generate(is_compatible=lambda p: True, call=_call)
        return provider, data, attempts_made
