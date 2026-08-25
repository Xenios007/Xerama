"""Shared shot/episode lookup helpers for media-production routers
(storyboards, video production, ...) - avoids duplicating the same
scene/shot search and episode->series resolution in every router."""

from fastapi import HTTPException

from xerama.api.authorization import authorize_project_access
from xerama.domain.auth import User
from xerama.domain.enums import ProjectRole
from xerama.domain.scene import EpisodeShotPlan, Scene, Shot
from xerama.repositories.interfaces import (
    EpisodeRecord,
    EpisodeRepository,
    ProjectMembershipRepository,
    SeriesRecord,
    SeriesRepository,
)


def find_shot(plan: EpisodeShotPlan, scene_number: int, shot_number: int) -> tuple[Scene, Shot]:
    for scene in plan.scenes:
        if scene.scene_number != scene_number:
            continue
        for shot in scene.shots:
            if shot.shot_number == shot_number:
                return scene, shot
    raise HTTPException(status_code=404, detail="scene/shot not found in the approved shot plan")


async def episode_context(
    episode_id: str,
    episode_repo: EpisodeRepository,
    series_repo: SeriesRepository,
    *,
    user: User | None = None,
    membership_repo: ProjectMembershipRepository | None = None,
    min_role: ProjectRole = ProjectRole.VIEWER,
) -> tuple[EpisodeRecord, SeriesRecord]:
    """Resolves episode -> series (which carries `project_id`).

    `user`/`membership_repo` are optional (MODULE-067): every one of this
    helper's ~16 call sites across storyboards/video_production/
    audio_production/assembly can opt into authorization by passing them,
    without each router having to duplicate the `authorize_project_access`
    call itself. Omitting both keeps the pre-MODULE-067 behavior exactly -
    a plain episode->series lookup, no authorization check."""
    episode = await episode_repo.get(episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="episode not found")
    series = await series_repo.get_series(episode.series_id)
    if series is None:
        raise HTTPException(status_code=404, detail="series not found")
    if membership_repo is not None:
        await authorize_project_access(series.project_id, min_role, user, membership_repo)
    return episode, series
