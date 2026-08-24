"""Subtitle track endpoints (MODULE-039)."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from xerama.api.deps import get_episode_repo, get_subtitle_service
from xerama.domain.quality import QCResult
from xerama.domain.subtitle import SubtitleCue
from xerama.repositories.interfaces import EpisodeRepository
from xerama.services.subtitle_service import SubtitleService

router = APIRouter(tags=["subtitles"])


@router.post("/episodes/{episode_id}/subtitles/generate", response_model=list[SubtitleCue])
async def generate_subtitles(
    episode_id: str,
    language: str = "en",
    service: SubtitleService = Depends(get_subtitle_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
) -> list[SubtitleCue]:
    """Deterministic from the approved shot plan - regenerating replaces
    every existing cue for this (episode, language), never accumulates."""
    plan = await episode_repo.get_shot_plan(episode_id)
    if plan is None:
        raise HTTPException(status_code=409, detail="episode has no shot plan yet")
    return await service.generate_track(episode_id, plan, language)


@router.get("/episodes/{episode_id}/subtitles", response_model=list[SubtitleCue])
async def list_subtitles(
    episode_id: str, language: str = "en", service: SubtitleService = Depends(get_subtitle_service)
) -> list[SubtitleCue]:
    return await service.list_by_episode(episode_id, language)


@router.get("/episodes/{episode_id}/subtitles/export.srt", response_class=PlainTextResponse)
async def export_subtitles_srt(
    episode_id: str, language: str = "en", service: SubtitleService = Depends(get_subtitle_service)
) -> str:
    return await service.export_srt(episode_id, language)


@router.get("/episodes/{episode_id}/subtitles/validate", response_model=QCResult)
async def validate_subtitles(
    episode_id: str, language: str = "en", service: SubtitleService = Depends(get_subtitle_service)
) -> QCResult:
    return await service.validate_readability(episode_id, language)
