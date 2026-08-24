"""Storyboard/keyframe workflow endpoints (Module 06).

"approved shot -> rough storyboard/layout -> compiled references -> final
keyframe -> QC state -> accept/retry."
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from xerama.api.deps import (
    get_episode_repo,
    get_image_router,
    get_series_repo,
    get_storyboard_service,
    get_style_bible_repo,
)
from xerama.api.shot_lookup import episode_context, find_shot
from xerama.domain.asset import Asset
from xerama.domain.storyboard import Storyboard
from xerama.pipeline.prompt_compiler import PromptCompiler
from xerama.providers.image import ImageProvider
from xerama.repositories.interfaces import EpisodeRepository, SeriesRepository, StyleBibleRepository
from xerama.services.media_router import MediaProviderRouter, NoEligibleProviderError
from xerama.services.storyboard_service import StoryboardService

router = APIRouter(tags=["storyboards"])


class StoryboardCreateRequest(BaseModel):
    layout_description: str = ""


@router.post(
    "/episodes/{episode_id}/scenes/{scene_number}/shots/{shot_number}/storyboard",
    response_model=Storyboard,
)
async def create_storyboard(
    episode_id: str,
    scene_number: int,
    shot_number: int,
    body: StoryboardCreateRequest | None = None,
    service: StoryboardService = Depends(get_storyboard_service),
) -> Storyboard:
    layout_description = body.layout_description if body else ""
    return await service.get_or_create_storyboard(
        episode_id, scene_number, shot_number, layout_description
    )


@router.get("/episodes/{episode_id}/storyboards", response_model=list[Storyboard])
async def list_storyboards(
    episode_id: str, service: StoryboardService = Depends(get_storyboard_service)
) -> list[Storyboard]:
    return await service.list_by_episode(episode_id)


@router.get("/storyboards/{storyboard_id}", response_model=Storyboard)
async def get_storyboard(
    storyboard_id: str, service: StoryboardService = Depends(get_storyboard_service)
) -> Storyboard:
    try:
        return await service.get(storyboard_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/storyboards/{storyboard_id}/keyframes/generate", response_model=Asset)
async def generate_keyframe(
    storyboard_id: str,
    service: StoryboardService = Depends(get_storyboard_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    style_bible_repo: StyleBibleRepository = Depends(get_style_bible_repo),
    image_router: MediaProviderRouter[ImageProvider] = Depends(get_image_router),
) -> Asset:
    try:
        storyboard = await service.get(storyboard_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    episode, series = await episode_context(storyboard.episode_id, episode_repo, series_repo)
    plan = await episode_repo.get_shot_plan(storyboard.episode_id)
    if plan is None:
        raise HTTPException(status_code=409, detail="episode has no shot plan yet")
    scene, shot = find_shot(plan, storyboard.scene_number, storyboard.shot_number)
    bible = await series_repo.get_bible(episode.series_id)
    if bible is None:
        raise HTTPException(status_code=409, detail="series has no approved Series Bible yet")
    cast = await series_repo.get_cast(episode.series_id)
    style_bible = await style_bible_repo.get_or_create(episode.series_id)
    request = PromptCompiler().compile_shot(shot, scene, cast, bible, style_bible)

    try:
        return await service.generate_keyframe(
            storyboard_id, series.project_id, request, image_router, series_id=episode.series_id
        )
    except NoEligibleProviderError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/storyboards/{storyboard_id}/keyframes/upload", response_model=Asset)
async def upload_keyframe(
    storyboard_id: str,
    file: UploadFile,
    service: StoryboardService = Depends(get_storyboard_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
) -> Asset:
    """Manual upload fallback - a first-class path, not degraded, so the
    workflow is never blocked purely by image-provider availability."""
    try:
        storyboard = await service.get(storyboard_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _, series = await episode_context(storyboard.episode_id, episode_repo, series_repo)

    data = await file.read()
    ext = "." + file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else ""
    return await service.upload_keyframe(
        storyboard_id,
        series.project_id,
        data,
        mime_type=file.content_type or "",
        ext=ext,
        series_id=series.id,
    )


@router.get("/storyboards/{storyboard_id}/keyframes", response_model=list[Asset])
async def list_keyframes(
    storyboard_id: str,
    service: StoryboardService = Depends(get_storyboard_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
) -> list[Asset]:
    try:
        storyboard = await service.get(storyboard_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _, series = await episode_context(storyboard.episode_id, episode_repo, series_repo)
    return await service.list_keyframes(series.project_id, storyboard)


@router.post("/storyboards/{storyboard_id}/keyframes/{asset_id}/accept", response_model=Storyboard)
async def accept_keyframe(
    storyboard_id: str, asset_id: str, service: StoryboardService = Depends(get_storyboard_service)
) -> Storyboard:
    try:
        return await service.accept_keyframe(storyboard_id, asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/storyboards/{storyboard_id}/keyframes/{asset_id}/reject", response_model=Asset)
async def reject_keyframe(
    storyboard_id: str,
    asset_id: str,
    reason: str,
    service: StoryboardService = Depends(get_storyboard_service),
) -> Asset:
    try:
        await service.get(storyboard_id)  # 404s if the storyboard itself is unknown
        return await service.reject_keyframe(asset_id, reason)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
