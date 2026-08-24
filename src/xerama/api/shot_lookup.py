"""Shared shot/episode lookup helpers for media-production routers
(storyboards, video production, ...) - avoids duplicating the same
scene/shot search and episode->series resolution in every router."""

from fastapi import HTTPException

from xerama.domain.scene import EpisodeShotPlan, Scene, Shot
from xerama.repositories.interfaces import EpisodeRecord, EpisodeRepository, SeriesRecord, SeriesRepository


def find_shot(plan: EpisodeShotPlan, scene_number: int, shot_number: int) -> tuple[Scene, Shot]:
    for scene in plan.scenes:
        if scene.scene_number != scene_number:
            continue
        for shot in scene.shots:
            if shot.shot_number == shot_number:
                return scene, shot
    raise HTTPException(status_code=404, detail="scene/shot not found in the approved shot plan")


async def episode_context(
    episode_id: str, episode_repo: EpisodeRepository, series_repo: SeriesRepository
) -> tuple[EpisodeRecord, SeriesRecord]:
    episode = await episode_repo.get(episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="episode not found")
    series = await series_repo.get_series(episode.series_id)
    if series is None:
        raise HTTPException(status_code=404, detail="series not found")
    return episode, series
