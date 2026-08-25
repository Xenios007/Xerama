"""Multi-Episode Engine endpoints (Module 02).

Generate one episode, the next unfinished episode, or a range - each call
is idempotent-safe (regenerating an episode retires its old canon commit
and marks later committed episodes STALE rather than corrupting them).
"""

from fastapi import APIRouter, Depends, HTTPException

from xerama.api.authorization import require_project_role
from xerama.api.deps import get_episode_engine
from xerama.domain.enums import ProjectRole
from xerama.pipeline.ai_gateway import XeramaGenerationError
from xerama.pipeline.episode_engine import EpisodeEngine, EpisodeGenerationResult

router = APIRouter(
    prefix="/series/{series_id}/episodes",
    tags=["episodes"],
    dependencies=[Depends(require_project_role(ProjectRole.EDITOR))],
)


@router.post("/{episode_number}/generate", response_model=EpisodeGenerationResult)
async def generate_episode(
    series_id: str,
    episode_number: int,
    project_id: str,
    engine: EpisodeEngine = Depends(get_episode_engine),
) -> EpisodeGenerationResult:
    try:
        return await engine.generate_episode(project_id, series_id, episode_number)
    except XeramaGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/generate-next", response_model=EpisodeGenerationResult)
async def generate_next_unfinished(
    series_id: str,
    project_id: str,
    engine: EpisodeEngine = Depends(get_episode_engine),
) -> EpisodeGenerationResult:
    try:
        return await engine.generate_next_unfinished(project_id, series_id)
    except XeramaGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/generate-range", response_model=list[EpisodeGenerationResult])
async def generate_range(
    series_id: str,
    project_id: str,
    start: int,
    end: int,
    engine: EpisodeEngine = Depends(get_episode_engine),
) -> list[EpisodeGenerationResult]:
    try:
        return await engine.generate_range(project_id, series_id, start, end)
    except XeramaGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
