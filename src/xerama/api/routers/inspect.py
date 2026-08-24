"""Read endpoints so every pipeline stage stays inspectable independent of
the synchronous POST /generate-series response - see README.md
"Every stage must be inspectable"."""

from fastapi import APIRouter, Depends, HTTPException

from xerama.api.deps import get_episode_repo, get_job_repo, get_series_repo
from xerama.domain.character import CharacterCast
from xerama.domain.generation_request import ShotGenerationRequest
from xerama.domain.scene import EpisodeShotPlan
from xerama.domain.story import SeriesBible
from xerama.pipeline.prompt_compiler import PromptCompiler
from xerama.repositories.interfaces import (
    EpisodeRecord,
    EpisodeRepository,
    JobRecord,
    JobRepository,
    SeriesRecord,
    SeriesRepository,
)

router = APIRouter(tags=["inspect"])


@router.get("/jobs/{job_id}", response_model=JobRecord)
async def get_job(job_id: str, repo: JobRepository = Depends(get_job_repo)) -> JobRecord:
    job = await repo.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.get("/series/{series_id}", response_model=SeriesRecord)
async def get_series(series_id: str, repo: SeriesRepository = Depends(get_series_repo)) -> SeriesRecord:
    series = await repo.get_series(series_id)
    if series is None:
        raise HTTPException(status_code=404, detail="series not found")
    return series


@router.get("/series/{series_id}/bible", response_model=SeriesBible)
async def get_bible(series_id: str, repo: SeriesRepository = Depends(get_series_repo)) -> SeriesBible:
    bible = await repo.get_bible(series_id)
    if bible is None:
        raise HTTPException(status_code=404, detail="series bible not found")
    return bible


@router.get("/series/{series_id}/characters", response_model=CharacterCast)
async def get_characters(
    series_id: str, repo: SeriesRepository = Depends(get_series_repo)
) -> CharacterCast:
    return await repo.get_cast(series_id)


@router.get("/series/{series_id}/episodes", response_model=list[EpisodeRecord])
async def list_episodes(
    series_id: str, repo: EpisodeRepository = Depends(get_episode_repo)
) -> list[EpisodeRecord]:
    return await repo.list_by_series(series_id)


@router.get("/episodes/{episode_id}", response_model=EpisodeRecord)
async def get_episode(
    episode_id: str, repo: EpisodeRepository = Depends(get_episode_repo)
) -> EpisodeRecord:
    episode = await repo.get(episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="episode not found")
    return episode


@router.get("/episodes/{episode_id}/shots", response_model=EpisodeShotPlan)
async def get_shot_plan(
    episode_id: str, repo: EpisodeRepository = Depends(get_episode_repo)
) -> EpisodeShotPlan:
    plan = await repo.get_shot_plan(episode_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="shot plan not found")
    return plan


@router.get("/episodes/{episode_id}/generation-requests", response_model=list[ShotGenerationRequest])
async def get_generation_requests(
    episode_id: str,
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
) -> list[ShotGenerationRequest]:
    """Compiles the approved shot plan into provider-neutral generation
    requests on demand - see modules/03_DIRECTOR_PROMPT_COMPILER.md.
    Deterministic and not persisted; recompiled fresh from current data."""
    episode = await episode_repo.get(episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="episode not found")
    plan = await episode_repo.get_shot_plan(episode_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="shot plan not found")
    bible = await series_repo.get_bible(episode.series_id)
    if bible is None:
        raise HTTPException(status_code=409, detail="series has no approved Series Bible yet")
    cast = await series_repo.get_cast(episode.series_id)
    return PromptCompiler().compile_episode(plan, cast, bible)
