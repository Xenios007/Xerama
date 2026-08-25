"""Sound effect cue endpoints (MODULE-038)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from xerama.api.authorization import get_current_user, get_project_membership_repo, require_episode_role
from xerama.api.deps import get_episode_repo, get_series_repo, get_sound_effect_cue_service
from xerama.api.shot_lookup import episode_context, find_shot
from xerama.domain.auth import User
from xerama.domain.enums import ProjectRole
from xerama.domain.rights import RightsMetadata
from xerama.domain.sound_effect import SoundEffectCue
from xerama.repositories.interfaces import EpisodeRepository, ProjectMembershipRepository, SeriesRepository
from xerama.services.sound_effect_service import CueNotReadyError, SoundEffectCueService

router = APIRouter(tags=["sound-effect-cues"])


async def _authorize_for_cue(
    cue_id: str,
    min_role: ProjectRole,
    service: SoundEffectCueService,
    episode_repo: EpisodeRepository,
    series_repo: SeriesRepository,
    user: User | None,
    membership_repo: ProjectMembershipRepository,
) -> SoundEffectCue:
    try:
        cue = await service.get(cue_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await episode_context(
        cue.episode_id, episode_repo, series_repo,
        user=user, membership_repo=membership_repo, min_role=min_role,
    )
    return cue


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


@router.post(
    "/episodes/{episode_id}/sound-effect-cues",
    response_model=SoundEffectCue,
    dependencies=[Depends(require_episode_role(ProjectRole.EDITOR))],
)
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
    dependencies=[Depends(require_episode_role(ProjectRole.EDITOR))],
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


@router.get(
    "/episodes/{episode_id}/sound-effect-cues",
    response_model=list[SoundEffectCue],
    dependencies=[Depends(require_episode_role(ProjectRole.VIEWER))],
)
async def list_sound_effect_cues(
    episode_id: str, service: SoundEffectCueService = Depends(get_sound_effect_cue_service)
) -> list[SoundEffectCue]:
    return await service.list_by_episode(episode_id)


@router.get("/sound-effect-cues/{cue_id}", response_model=SoundEffectCue)
async def get_sound_effect_cue(
    cue_id: str,
    service: SoundEffectCueService = Depends(get_sound_effect_cue_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> SoundEffectCue:
    return await _authorize_for_cue(
        cue_id, ProjectRole.VIEWER, service, episode_repo, series_repo, user, membership_repo
    )


@router.post("/sound-effect-cues/{cue_id}/link-asset", response_model=SoundEffectCue)
async def link_sound_effect_cue_asset(
    cue_id: str,
    body: LinkAssetRequest,
    service: SoundEffectCueService = Depends(get_sound_effect_cue_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> SoundEffectCue:
    await _authorize_for_cue(
        cue_id, ProjectRole.EDITOR, service, episode_repo, series_repo, user, membership_repo
    )
    try:
        return await service.link_asset(cue_id, body.asset_id, body.rights)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sound-effect-cues/{cue_id}/approve", response_model=SoundEffectCue)
async def approve_sound_effect_cue(
    cue_id: str,
    service: SoundEffectCueService = Depends(get_sound_effect_cue_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> SoundEffectCue:
    await _authorize_for_cue(
        cue_id, ProjectRole.EDITOR, service, episode_repo, series_repo, user, membership_repo
    )
    try:
        return await service.approve_cue(cue_id)
    except (PermissionError, CueNotReadyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/sound-effect-cues/{cue_id}", status_code=204)
async def delete_sound_effect_cue(
    cue_id: str,
    service: SoundEffectCueService = Depends(get_sound_effect_cue_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> None:
    await _authorize_for_cue(
        cue_id, ProjectRole.OWNER, service, episode_repo, series_repo, user, membership_repo
    )
    await service.delete_cue(cue_id)
