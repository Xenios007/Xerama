"""Shot dialogue/audio production endpoints (MODULE-035)."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from xerama.api.deps import (
    get_audio_production_service,
    get_cost_service,
    get_episode_repo,
    get_retake_service,
    get_series_repo,
    get_voice_router,
)
from xerama.api.shot_lookup import episode_context, find_shot
from xerama.domain.asset import Asset
from xerama.domain.audio_production import ShotAudioProduction
from xerama.providers.voice import VoiceProvider
from xerama.repositories.interfaces import EpisodeRepository, SeriesRepository
from xerama.services.audio_production_service import AudioProductionService
from xerama.services.cost_service import CostRecordService
from xerama.services.media_qc_service import QCGateBlockedError
from xerama.services.media_router import MediaProviderRouter, NoEligibleProviderError
from xerama.services.retake_service import AutomaticRetakeService

router = APIRouter(tags=["audio-production"])


class DialogueTakeRequest(BaseModel):
    character_id: str
    text: str | None = None  # defaults to the shot's own scripted dialogue


@router.post(
    "/episodes/{episode_id}/scenes/{scene_number}/shots/{shot_number}/audio-production",
    response_model=ShotAudioProduction,
)
async def create_audio_production(
    episode_id: str,
    scene_number: int,
    shot_number: int,
    service: AudioProductionService = Depends(get_audio_production_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
) -> ShotAudioProduction:
    """Idempotent get-or-create. `audio_mode` is read from the approved
    shot plan (not client-supplied) so it always matches the Director's
    actual data."""
    plan = await episode_repo.get_shot_plan(episode_id)
    if plan is None:
        raise HTTPException(status_code=409, detail="episode has no shot plan yet")
    _, shot = find_shot(plan, scene_number, shot_number)
    return await service.get_or_create_production(
        episode_id, scene_number, shot_number, shot.audio_mode
    )


@router.get("/episodes/{episode_id}/audio-productions", response_model=list[ShotAudioProduction])
async def list_audio_productions(
    episode_id: str, service: AudioProductionService = Depends(get_audio_production_service)
) -> list[ShotAudioProduction]:
    return await service.list_by_episode(episode_id)


@router.get("/audio-productions/{production_id}", response_model=ShotAudioProduction)
async def get_audio_production(
    production_id: str, service: AudioProductionService = Depends(get_audio_production_service)
) -> ShotAudioProduction:
    try:
        return await service.get(production_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/audio-productions/{production_id}/takes/generate", response_model=Asset)
async def generate_dialogue_take(
    production_id: str,
    body: DialogueTakeRequest,
    service: AudioProductionService = Depends(get_audio_production_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    voice_router: MediaProviderRouter[VoiceProvider] = Depends(get_voice_router),
    cost_service: CostRecordService = Depends(get_cost_service),
) -> Asset:
    try:
        production = await service.get(production_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    episode, series = await episode_context(production.episode_id, episode_repo, series_repo)
    text = body.text
    if text is None:
        plan = await episode_repo.get_shot_plan(production.episode_id)
        if plan is None:
            raise HTTPException(status_code=409, detail="episode has no shot plan yet")
        _, shot = find_shot(plan, production.scene_number, production.shot_number)
        text = shot.dialogue
        if not text:
            raise HTTPException(
                status_code=422, detail="shot has no scripted dialogue - pass text explicitly"
            )

    try:
        asset = await service.generate_dialogue_take(
            production_id, series.project_id, body.character_id, text, voice_router,
            series_id=episode.series_id,
        )
    except NoEligibleProviderError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await cost_service.record_generation_attempts(
        asset,
        stage="voice_generation",
        project_id=series.project_id,
        series_id=episode.series_id,
        episode_id=production.episode_id,
        scene_number=production.scene_number,
        shot_number=production.shot_number,
        quantity=float(len(text)),
        unit="characters",
    )
    return asset


@router.post("/audio-productions/{production_id}/takes/auto-heal", response_model=Asset)
async def generate_dialogue_take_with_auto_heal(
    production_id: str,
    body: DialogueTakeRequest,
    service: AudioProductionService = Depends(get_audio_production_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    voice_router: MediaProviderRouter[VoiceProvider] = Depends(get_voice_router),
    retake_service: AutomaticRetakeService = Depends(get_retake_service),
) -> Asset:
    """MODULE-045 - see storyboards.py's `generate_keyframe_with_auto_heal`;
    same generate -> QC-gate -> repair-and-retry loop for dialogue takes."""
    try:
        production = await service.get(production_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    episode, series = await episode_context(production.episode_id, episode_repo, series_repo)
    text = body.text
    if text is None:
        plan = await episode_repo.get_shot_plan(production.episode_id)
        if plan is None:
            raise HTTPException(status_code=409, detail="episode has no shot plan yet")
        _, shot = find_shot(plan, production.scene_number, production.shot_number)
        text = shot.dialogue
        if not text:
            raise HTTPException(
                status_code=422, detail="shot has no scripted dialogue - pass text explicitly"
            )

    try:
        asset, _ = await service.generate_with_auto_heal(
            production_id, series.project_id, body.character_id, text, voice_router, retake_service,
            series_id=episode.series_id,
        )
        return asset
    except NoEligibleProviderError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except QCGateBlockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/audio-productions/{production_id}/takes/upload", response_model=Asset)
async def upload_dialogue_take(
    production_id: str,
    file: UploadFile,
    service: AudioProductionService = Depends(get_audio_production_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
) -> Asset:
    """Manual upload fallback - a first-class path, not degraded."""
    try:
        production = await service.get(production_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _, series = await episode_context(production.episode_id, episode_repo, series_repo)

    data = await file.read()
    ext = "." + file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else ""
    return await service.upload_dialogue_take(
        production_id, series.project_id, data, mime_type=file.content_type or "", ext=ext,
        series_id=series.id,
    )


@router.get("/audio-productions/{production_id}/takes", response_model=list[Asset])
async def list_dialogue_takes(
    production_id: str,
    service: AudioProductionService = Depends(get_audio_production_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
) -> list[Asset]:
    try:
        production = await service.get(production_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _, series = await episode_context(production.episode_id, episode_repo, series_repo)
    return await service.list_takes(series.project_id, production)


@router.post(
    "/audio-productions/{production_id}/takes/{asset_id}/accept", response_model=ShotAudioProduction
)
async def accept_dialogue_take(
    production_id: str,
    asset_id: str,
    service: AudioProductionService = Depends(get_audio_production_service),
) -> ShotAudioProduction:
    try:
        return await service.accept_take(production_id, asset_id)
    except QCGateBlockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/audio-productions/{production_id}/takes/{asset_id}/reject", response_model=Asset)
async def reject_dialogue_take(
    production_id: str,
    asset_id: str,
    reason: str,
    service: AudioProductionService = Depends(get_audio_production_service),
) -> Asset:
    try:
        await service.get(production_id)  # 404s if the production record itself is unknown
        return await service.reject_take(asset_id, reason)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
