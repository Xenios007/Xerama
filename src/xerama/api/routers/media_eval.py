"""Media evaluation harness endpoints (MODULE-073).

Not project-scoped - a benchmark run compares image/video *providers* by
shot class, not any single user's production data (same reasoning as
MODULE-072's `/eval` endpoints and MODULE-067's `GET /jobs/queued`). In
hosted mode it still requires *some* authenticated caller - a live run
spends real provider credits.
"""

from fastapi import APIRouter, Depends, HTTPException

from xerama.api.authorization import get_current_user
from xerama.api.deps import get_media_eval_service
from xerama.config import get_settings
from xerama.domain.asset import AssetType
from xerama.domain.auth import User
from xerama.domain.media_eval import MediaEvalRunResult
from xerama.pipeline.media_eval_aggregation import ShotClassProviderBenchmark
from xerama.services.media_eval_service import MediaEvalService

router = APIRouter(prefix="/media-eval", tags=["media-eval"])


async def _require_authenticated_in_hosted_mode(user: User | None = Depends(get_current_user)) -> None:
    if get_settings().xerama_mode == "hosted" and user is None:
        raise HTTPException(status_code=401, detail="authentication required")


@router.post(
    "/{asset_type}/run",
    response_model=list[MediaEvalRunResult],
    dependencies=[Depends(_require_authenticated_in_hosted_mode)],
)
async def run_media_eval_dataset(
    asset_type: AssetType, service: MediaEvalService = Depends(get_media_eval_service)
) -> list[MediaEvalRunResult]:
    """"Live eval opt-in" - the only way a benchmark run happens. Runs
    every curated case for `asset_type` (image or video) against the
    currently configured provider router and persists each result,
    including real QC scoring (MODULE-044) and asset persistence
    (ADR-020)."""
    return await service.run_dataset(asset_type)


@router.get("/benchmark", response_model=list[ShotClassProviderBenchmark])
async def get_shot_class_benchmark(
    service: MediaEvalService = Depends(get_media_eval_service),
) -> list[ShotClassProviderBenchmark]:
    """"Provider routing can be informed by repeatable media
    benchmarks" - every provider that has ever been run against any
    shot class, grouped and summarized separately per (shot_class,
    provider)."""
    return await service.benchmark_by_shot_class()


@router.post("/runs/{run_id}/human-preference", response_model=MediaEvalRunResult)
async def record_media_eval_human_preference(
    run_id: str, preference: str, service: MediaEvalService = Depends(get_media_eval_service)
) -> MediaEvalRunResult:
    try:
        return await service.record_human_preference(run_id, preference)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
