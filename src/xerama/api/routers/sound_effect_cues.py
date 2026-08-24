"""Sound effect cue endpoints (MODULE-038)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from xerama.api.deps import get_episode_repo, get_sound_effect_cue_service
from xerama.api.shot_lookup import find_shot
from xerama.domain.rights import RightsMetadata
from xerama.domain.sound_effect import SoundEffectCue
from xerama.repositories.interfaces import EpisodeRepository
from xerama.services.sound_effect_service import CueNotReadyError, SoundEffectCueService

router = APIRouter(tags=["sound-effect-cues"])


class SoundEffectCueCreateRequest(BaseModel):
    scene_number: int
    description: str
    start_seconds: float
    end_seconds: float
    shot_number: int | None = None
    gain_db: float = 0.0


class LinkAssetRequest(BaseModel):
    asset_id: str
    rights: RightsMetadata = RightsMetadata()


@router.post("/episodes/{episode_id}/sound-effect-cues", response_model=SoundEffectCue)
async def create_sound_effect_cue(
    episode_id: str,
    body: SoundEffectCueCreateRequest,
    service: SoundEffectCueService = Depends(get_sound_effect_cue_service),
) -> SoundEffectCue:
    return await service.create_cue(
        episode_id,
        body.scene_number,
        body.description,
        body.start_seconds,
        body.end_seconds,
        shot_number=body.shot_number,
        gain_db=body.gain_db,
    )


@router.post(
    "/episodes/{episode_id}/scenes/{scene_number}/shots/{shot_number}/sound-effect-cues/derive",
    response_model=list[SoundEffectCue],
)
async def derive_sound_effect_cues(
    episode_id: str,
    scene_number: int,
    shot_number: int,
    service: SoundEffectCueService = Depends(get_sound_effect_cue_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
) -> list[SoundEffectCue]:
    """Deterministic keyword-based candidates from the shot's action/
    micro-beats (`pipeline/sfx_derivation.py`), persisted as draft cues."""
    plan = await episode_repo.get_shot_plan(episode_id)
    if plan is None:
        raise HTTPException(status_code=409, detail="episode has no shot plan yet")
    _, shot = find_shot(plan, scene_number, shot_number)
    return await service.derive_candidates_for_shot(episode_id, scene_number, shot)


@router.get("/episodes/{episode_id}/sound-effect-cues", response_model=list[SoundEffectCue])
async def list_sound_effect_cues(
    episode_id: str, service: SoundEffectCueService = Depends(get_sound_effect_cue_service)
) -> list[SoundEffectCue]:
    return await service.list_by_episode(episode_id)


@router.get("/sound-effect-cues/{cue_id}", response_model=SoundEffectCue)
async def get_sound_effect_cue(
    cue_id: str, service: SoundEffectCueService = Depends(get_sound_effect_cue_service)
) -> SoundEffectCue:
    try:
        return await service.get(cue_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sound-effect-cues/{cue_id}/link-asset", response_model=SoundEffectCue)
async def link_sound_effect_cue_asset(
    cue_id: str,
    body: LinkAssetRequest,
    service: SoundEffectCueService = Depends(get_sound_effect_cue_service),
) -> SoundEffectCue:
    try:
        return await service.link_asset(cue_id, body.asset_id, body.rights)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sound-effect-cues/{cue_id}/approve", response_model=SoundEffectCue)
async def approve_sound_effect_cue(
    cue_id: str, service: SoundEffectCueService = Depends(get_sound_effect_cue_service)
) -> SoundEffectCue:
    try:
        return await service.approve_cue(cue_id)
    except (PermissionError, CueNotReadyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/sound-effect-cues/{cue_id}", status_code=204)
async def delete_sound_effect_cue(
    cue_id: str, service: SoundEffectCueService = Depends(get_sound_effect_cue_service)
) -> None:
    await service.delete_cue(cue_id)
