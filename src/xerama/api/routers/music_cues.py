"""Music cue planning endpoints (MODULE-037)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from xerama.api.authorization import get_current_user, get_project_membership_repo, require_episode_role
from xerama.api.deps import get_episode_repo, get_music_cue_service, get_series_repo
from xerama.api.shot_lookup import episode_context
from xerama.domain.auth import User
from xerama.domain.enums import ProjectRole
from xerama.domain.music import MusicCue
from xerama.domain.rights import RightsMetadata
from xerama.repositories.interfaces import EpisodeRepository, ProjectMembershipRepository, SeriesRepository
from xerama.services.music_cue_service import CueNotReadyError, MusicCueService

router = APIRouter(tags=["music-cues"])


async def _authorize_for_cue(
    cue_id: str,
    min_role: ProjectRole,
    service: MusicCueService,
    episode_repo: EpisodeRepository,
    series_repo: SeriesRepository,
    user: User | None,
    membership_repo: ProjectMembershipRepository,
) -> MusicCue:
    try:
        cue = await service.get(cue_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await episode_context(
        cue.episode_id, episode_repo, series_repo,
        user=user, membership_repo=membership_repo, min_role=min_role,
    )
    return cue


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


@router.post(
    "/episodes/{episode_id}/music-cues",
    response_model=MusicCue,
    dependencies=[Depends(require_episode_role(ProjectRole.EDITOR))],
)
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


@router.get(
    "/episodes/{episode_id}/music-cues",
    response_model=list[MusicCue],
    dependencies=[Depends(require_episode_role(ProjectRole.VIEWER))],
)
async def list_music_cues(
    episode_id: str, service: MusicCueService = Depends(get_music_cue_service)
) -> list[MusicCue]:
    return await service.list_by_episode(episode_id)


@router.get("/music-cues/{cue_id}", response_model=MusicCue)
async def get_music_cue(
    cue_id: str,
    service: MusicCueService = Depends(get_music_cue_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> MusicCue:
    return await _authorize_for_cue(
        cue_id, ProjectRole.VIEWER, service, episode_repo, series_repo, user, membership_repo
    )


@router.post("/music-cues/{cue_id}/link-asset", response_model=MusicCue)
async def link_music_cue_asset(
    cue_id: str,
    body: LinkAssetRequest,
    service: MusicCueService = Depends(get_music_cue_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> MusicCue:
    await _authorize_for_cue(
        cue_id, ProjectRole.EDITOR, service, episode_repo, series_repo, user, membership_repo
    )
    try:
        return await service.link_asset(cue_id, body.asset_id, body.rights)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/music-cues/{cue_id}/approve", response_model=MusicCue)
async def approve_music_cue(
    cue_id: str,
    service: MusicCueService = Depends(get_music_cue_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> MusicCue:
    await _authorize_for_cue(
        cue_id, ProjectRole.EDITOR, service, episode_repo, series_repo, user, membership_repo
    )
    try:
        return await service.approve_cue(cue_id)
    except (PermissionError, CueNotReadyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/music-cues/{cue_id}", status_code=204)
async def delete_music_cue(
    cue_id: str,
    service: MusicCueService = Depends(get_music_cue_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> None:
    await _authorize_for_cue(
        cue_id, ProjectRole.OWNER, service, episode_repo, series_repo, user, membership_repo
    )
    await service.delete_cue(cue_id)
