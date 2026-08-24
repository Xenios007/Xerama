"""Music cue planning endpoints (MODULE-037)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from xerama.api.deps import get_music_cue_service
from xerama.domain.music import MusicCue
from xerama.domain.rights import RightsMetadata
from xerama.services.music_cue_service import CueNotReadyError, MusicCueService

router = APIRouter(tags=["music-cues"])


class MusicCueCreateRequest(BaseModel):
    purpose: str = ""
    mood: str = ""
    start_seconds: float
    end_seconds: float
    ducking_db: float = 0.0
    scene_number: int | None = None


class LinkAssetRequest(BaseModel):
    asset_id: str
    rights: RightsMetadata = RightsMetadata()


@router.post("/episodes/{episode_id}/music-cues", response_model=MusicCue)
async def create_music_cue(
    episode_id: str,
    body: MusicCueCreateRequest,
    service: MusicCueService = Depends(get_music_cue_service),
) -> MusicCue:
    return await service.create_cue(
        episode_id,
        body.purpose,
        body.mood,
        body.start_seconds,
        body.end_seconds,
        ducking_db=body.ducking_db,
        scene_number=body.scene_number,
    )


@router.get("/episodes/{episode_id}/music-cues", response_model=list[MusicCue])
async def list_music_cues(
    episode_id: str, service: MusicCueService = Depends(get_music_cue_service)
) -> list[MusicCue]:
    return await service.list_by_episode(episode_id)


@router.get("/music-cues/{cue_id}", response_model=MusicCue)
async def get_music_cue(
    cue_id: str, service: MusicCueService = Depends(get_music_cue_service)
) -> MusicCue:
    try:
        return await service.get(cue_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/music-cues/{cue_id}/link-asset", response_model=MusicCue)
async def link_music_cue_asset(
    cue_id: str, body: LinkAssetRequest, service: MusicCueService = Depends(get_music_cue_service)
) -> MusicCue:
    try:
        return await service.link_asset(cue_id, body.asset_id, body.rights)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/music-cues/{cue_id}/approve", response_model=MusicCue)
async def approve_music_cue(
    cue_id: str, service: MusicCueService = Depends(get_music_cue_service)
) -> MusicCue:
    try:
        return await service.approve_cue(cue_id)
    except (PermissionError, CueNotReadyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/music-cues/{cue_id}", status_code=204)
async def delete_music_cue(
    cue_id: str, service: MusicCueService = Depends(get_music_cue_service)
) -> None:
    await service.delete_cue(cue_id)
