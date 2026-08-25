"""Shot video-take production endpoints (MODULE-032, formerly Module 08).

"Given approved keyframes, Xerama can produce durable shot videos with
traceable takes and continuity metadata using fake providers end to end."
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from xerama.api.authorization import get_current_user, get_project_membership_repo
from xerama.api.deps import (
    get_asset_service,
    get_cost_service,
    get_episode_repo,
    get_lip_sync_router,
    get_retake_service,
    get_series_repo,
    get_storyboard_service,
    get_style_bible_repo,
    get_video_production_service,
    get_video_router,
)
from xerama.api.shot_lookup import episode_context, find_shot
from xerama.domain.asset import Asset
from xerama.domain.auth import User
from xerama.domain.enums import ProjectRole
from xerama.domain.video_production import ShotVideoProduction
from xerama.pipeline.prompt_compiler import PromptCompiler
from xerama.providers.lip_sync import LipSyncProvider
from xerama.providers.video import VideoProvider
from xerama.repositories.interfaces import (
    EpisodeRepository,
    ProjectMembershipRepository,
    SeriesRepository,
    StyleBibleRepository,
)
from xerama.services.asset_service import AssetService
from xerama.services.cost_service import CostRecordService
from xerama.services.media_router import MediaProviderRouter, NoEligibleProviderError
from xerama.services.retake_service import AutomaticRetakeService
from xerama.services.storyboard_service import StoryboardService
from xerama.services.media_qc_service import QCGateBlockedError
from xerama.services.video_production_service import (
    ContinuityOrderingError,
    LipSyncEligibilityError,
    VideoProductionService,
)

router = APIRouter(tags=["video-production"])


class LipSyncTakeRequest(BaseModel):
    source_video_asset_id: str
    source_audio_asset_id: str
    duration_seconds: float
    aspect_ratio: str = "9:16"
    character_id: str | None = None


@router.post(
    "/episodes/{episode_id}/scenes/{scene_number}/shots/{shot_number}/video-production",
    response_model=ShotVideoProduction,
)
async def create_video_production(
    episode_id: str,
    scene_number: int,
    shot_number: int,
    service: VideoProductionService = Depends(get_video_production_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> ShotVideoProduction:
    """Idempotent get-or-create. `continuity_group` is read from the
    approved shot plan (not client-supplied) so continuity sequencing
    always matches the Director's actual data."""
    await episode_context(
        episode_id, episode_repo, series_repo,
        user=user, membership_repo=membership_repo, min_role=ProjectRole.EDITOR,
    )
    plan = await episode_repo.get_shot_plan(episode_id)
    if plan is None:
        raise HTTPException(status_code=409, detail="episode has no shot plan yet")
    _, shot = find_shot(plan, scene_number, shot_number)
    return await service.get_or_create_production(
        episode_id, scene_number, shot_number, shot.continuity_group
    )


@router.get("/episodes/{episode_id}/video-productions", response_model=list[ShotVideoProduction])
async def list_video_productions(
    episode_id: str,
    service: VideoProductionService = Depends(get_video_production_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> list[ShotVideoProduction]:
    await episode_context(
        episode_id, episode_repo, series_repo,
        user=user, membership_repo=membership_repo, min_role=ProjectRole.VIEWER,
    )
    return await service.list_by_episode(episode_id)


@router.get("/video-productions/{production_id}", response_model=ShotVideoProduction)
async def get_video_production(
    production_id: str,
    service: VideoProductionService = Depends(get_video_production_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> ShotVideoProduction:
    try:
        production = await service.get(production_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await episode_context(
        production.episode_id, episode_repo, series_repo,
        user=user, membership_repo=membership_repo, min_role=ProjectRole.VIEWER,
    )
    return production


@router.post("/video-productions/{production_id}/takes/generate", response_model=Asset)
async def generate_take(
    production_id: str,
    service: VideoProductionService = Depends(get_video_production_service),
    storyboard_service: StoryboardService = Depends(get_storyboard_service),
    asset_service: AssetService = Depends(get_asset_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    style_bible_repo: StyleBibleRepository = Depends(get_style_bible_repo),
    video_router: MediaProviderRouter[VideoProvider] = Depends(get_video_router),
    cost_service: CostRecordService = Depends(get_cost_service),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> Asset:
    try:
        production = await service.get(production_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    episode, series = await episode_context(
        production.episode_id, episode_repo, series_repo,
        user=user, membership_repo=membership_repo, min_role=ProjectRole.EDITOR,
    )
    plan = await episode_repo.get_shot_plan(production.episode_id)
    if plan is None:
        raise HTTPException(status_code=409, detail="episode has no shot plan yet")
    scene, shot = find_shot(plan, production.scene_number, production.shot_number)
    bible = await series_repo.get_bible(episode.series_id)
    if bible is None:
        raise HTTPException(status_code=409, detail="series has no approved Series Bible yet")
    cast = await series_repo.get_cast(episode.series_id)
    style_bible = await style_bible_repo.get_or_create(episode.series_id)
    request = PromptCompiler().compile_shot(shot, scene, cast, bible, style_bible)

    keyframe_bytes = None
    storyboard = await storyboard_service.get_or_create_storyboard(
        production.episode_id, production.scene_number, production.shot_number
    )
    if storyboard.status == "approved" and storyboard.approved_keyframe_asset_id:
        try:
            keyframe_bytes = await asset_service.read_bytes(storyboard.approved_keyframe_asset_id)
        except FileNotFoundError:
            keyframe_bytes = None

    try:
        asset = await service.generate_take(
            production_id,
            series.project_id,
            request,
            video_router,
            keyframe_bytes=keyframe_bytes,
            series_id=episode.series_id,
        )
    except NoEligibleProviderError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ContinuityOrderingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await cost_service.record_generation_attempts(
        asset,
        stage="video_generation",
        project_id=series.project_id,
        series_id=episode.series_id,
        episode_id=production.episode_id,
        scene_number=production.scene_number,
        shot_number=production.shot_number,
        quantity=request.duration_seconds,
        unit="seconds",
    )
    return asset


@router.post("/video-productions/{production_id}/takes/auto-heal", response_model=Asset)
async def generate_take_with_auto_heal(
    production_id: str,
    service: VideoProductionService = Depends(get_video_production_service),
    storyboard_service: StoryboardService = Depends(get_storyboard_service),
    asset_service: AssetService = Depends(get_asset_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    style_bible_repo: StyleBibleRepository = Depends(get_style_bible_repo),
    video_router: MediaProviderRouter[VideoProvider] = Depends(get_video_router),
    retake_service: AutomaticRetakeService = Depends(get_retake_service),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> Asset:
    """MODULE-045 - see storyboards.py's `generate_keyframe_with_auto_heal`;
    same generate -> QC-gate -> repair-and-retry loop for video takes."""
    try:
        production = await service.get(production_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    episode, series = await episode_context(
        production.episode_id, episode_repo, series_repo,
        user=user, membership_repo=membership_repo, min_role=ProjectRole.EDITOR,
    )
    plan = await episode_repo.get_shot_plan(production.episode_id)
    if plan is None:
        raise HTTPException(status_code=409, detail="episode has no shot plan yet")
    scene, shot = find_shot(plan, production.scene_number, production.shot_number)
    bible = await series_repo.get_bible(episode.series_id)
    if bible is None:
        raise HTTPException(status_code=409, detail="series has no approved Series Bible yet")
    cast = await series_repo.get_cast(episode.series_id)
    style_bible = await style_bible_repo.get_or_create(episode.series_id)
    request = PromptCompiler().compile_shot(shot, scene, cast, bible, style_bible)

    keyframe_bytes = None
    storyboard = await storyboard_service.get_or_create_storyboard(
        production.episode_id, production.scene_number, production.shot_number
    )
    if storyboard.status == "approved" and storyboard.approved_keyframe_asset_id:
        try:
            keyframe_bytes = await asset_service.read_bytes(storyboard.approved_keyframe_asset_id)
        except FileNotFoundError:
            keyframe_bytes = None

    try:
        asset, _ = await service.generate_with_auto_heal(
            production_id,
            series.project_id,
            request,
            video_router,
            retake_service,
            keyframe_bytes=keyframe_bytes,
            series_id=episode.series_id,
            character_reference_ids=list(request.references.character_asset_ids),
        )
        return asset
    except NoEligibleProviderError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ContinuityOrderingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except QCGateBlockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/video-productions/{production_id}/takes/lip-sync", response_model=Asset)
async def generate_lip_synced_take(
    production_id: str,
    body: LipSyncTakeRequest,
    service: VideoProductionService = Depends(get_video_production_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    lip_sync_router: MediaProviderRouter[LipSyncProvider] = Depends(get_lip_sync_router),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> Asset:
    """Synchronize a controlled dialogue take (MODULE-034/035) onto this
    shot's video (MODULE-036) - only when native audio is insufficient."""
    try:
        production = await service.get(production_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _, series = await episode_context(
        production.episode_id, episode_repo, series_repo,
        user=user, membership_repo=membership_repo, min_role=ProjectRole.EDITOR,
    )

    blocking_plan = None
    if body.character_id:
        plan = await episode_repo.get_shot_plan(production.episode_id)
        if plan is not None:
            _, shot = find_shot(plan, production.scene_number, production.shot_number)
            blocking_plan = shot.blocking_plan

    try:
        return await service.generate_lip_synced_take(
            production_id,
            series.project_id,
            body.source_video_asset_id,
            body.source_audio_asset_id,
            lip_sync_router,
            body.duration_seconds,
            aspect_ratio=body.aspect_ratio,
            character_id=body.character_id,
            blocking_plan=blocking_plan,
            series_id=series.id,
        )
    except NoEligibleProviderError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LipSyncEligibilityError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc


@router.post("/video-productions/{production_id}/takes/upload", response_model=Asset)
async def upload_take(
    production_id: str,
    file: UploadFile,
    service: VideoProductionService = Depends(get_video_production_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> Asset:
    """Manual upload fallback - a first-class path, not degraded."""
    try:
        production = await service.get(production_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _, series = await episode_context(
        production.episode_id, episode_repo, series_repo,
        user=user, membership_repo=membership_repo, min_role=ProjectRole.EDITOR,
    )

    data = await file.read()
    ext = "." + file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else ""
    return await service.upload_take(
        production_id,
        series.project_id,
        data,
        mime_type=file.content_type or "",
        ext=ext,
        series_id=series.id,
    )


@router.get("/video-productions/{production_id}/takes", response_model=list[Asset])
async def list_takes(
    production_id: str,
    service: VideoProductionService = Depends(get_video_production_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> list[Asset]:
    try:
        production = await service.get(production_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _, series = await episode_context(
        production.episode_id, episode_repo, series_repo,
        user=user, membership_repo=membership_repo, min_role=ProjectRole.VIEWER,
    )
    return await service.list_takes(series.project_id, production)


@router.post(
    "/video-productions/{production_id}/takes/{asset_id}/accept", response_model=ShotVideoProduction
)
async def accept_take(
    production_id: str,
    asset_id: str,
    service: VideoProductionService = Depends(get_video_production_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> ShotVideoProduction:
    try:
        production = await service.get(production_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await episode_context(
        production.episode_id, episode_repo, series_repo,
        user=user, membership_repo=membership_repo, min_role=ProjectRole.EDITOR,
    )
    try:
        return await service.accept_take(production_id, asset_id)
    except QCGateBlockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/video-productions/{production_id}/takes/{asset_id}/reject", response_model=Asset)
async def reject_take(
    production_id: str,
    asset_id: str,
    reason: str,
    service: VideoProductionService = Depends(get_video_production_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> Asset:
    try:
        production = await service.get(production_id)  # 404s if the production record itself is unknown
        await episode_context(
            production.episode_id, episode_repo, series_repo,
            user=user, membership_repo=membership_repo, min_role=ProjectRole.EDITOR,
        )
        return await service.reject_take(asset_id, reason)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
