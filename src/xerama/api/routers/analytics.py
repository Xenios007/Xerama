"""Performance analytics endpoints (MODULE-061/062/063)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from xerama.api.authorization import (
    authorize_project_access,
    get_current_user,
    get_project_membership_repo,
)
from xerama.api.deps import (
    get_analytics_service,
    get_episode_repo,
    get_retention_service,
    get_series_repo,
    get_story_performance_service,
)
from xerama.api.shot_lookup import episode_context
from xerama.domain.analytics import EpisodeMetric
from xerama.domain.auth import User
from xerama.domain.enums import ProjectRole
from xerama.pipeline.retention_analytics import RetentionSummary, ShotDropPoint
from xerama.pipeline.story_performance import StoryPerformanceInsight
from xerama.repositories.interfaces import EpisodeRepository, ProjectMembershipRepository, SeriesRepository
from xerama.services.analytics_service import (
    AnalyticsIngestionService,
    RetentionAnalyticsService,
    StoryPerformanceLearningService,
)

router = APIRouter(tags=["analytics"])


class ImportMetricsRequest(BaseModel):
    render_version: int
    source: str = "manual_import"
    observation_window_start: datetime
    observation_window_end: datetime
    payload: dict = {}


async def _authorize_for_episode(
    episode_id: str,
    episode_repo: EpisodeRepository,
    series_repo: SeriesRepository,
    min_role: ProjectRole,
    user: User | None,
    membership_repo: ProjectMembershipRepository,
) -> None:
    _, series = await episode_context(episode_id, episode_repo, series_repo)
    await authorize_project_access(series.project_id, min_role, user, membership_repo)


@router.post("/episodes/{episode_id}/metrics/import", response_model=EpisodeMetric)
async def import_episode_metrics(
    episode_id: str,
    body: ImportMetricsRequest,
    service: AnalyticsIngestionService = Depends(get_analytics_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> EpisodeMetric:
    """See MODULE-061 - the manual/import adapter; re-posting the same
    (render_version, source, window) updates that row (deduplication)."""
    await _authorize_for_episode(
        episode_id, episode_repo, series_repo, ProjectRole.EDITOR, user, membership_repo
    )
    return await service.import_metrics(
        episode_id,
        body.render_version,
        body.source,
        body.observation_window_start,
        body.observation_window_end,
        body.payload,
    )


@router.get("/episodes/{episode_id}/metrics", response_model=list[EpisodeMetric])
async def list_episode_metrics(
    episode_id: str,
    service: AnalyticsIngestionService = Depends(get_analytics_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> list[EpisodeMetric]:
    await _authorize_for_episode(
        episode_id, episode_repo, series_repo, ProjectRole.VIEWER, user, membership_repo
    )
    return await service.list_metrics(episode_id)


@router.get("/episodes/{episode_id}/retention-summary", response_model=RetentionSummary)
async def get_retention_summary(
    episode_id: str,
    service: RetentionAnalyticsService = Depends(get_retention_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> RetentionSummary:
    await _authorize_for_episode(
        episode_id, episode_repo, series_repo, ProjectRole.VIEWER, user, membership_repo
    )
    return await service.get_summary(episode_id)


@router.get("/episodes/{episode_id}/retention-drop-points", response_model=list[ShotDropPoint])
async def get_retention_drop_points(
    episode_id: str,
    service: RetentionAnalyticsService = Depends(get_retention_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> list[ShotDropPoint]:
    await _authorize_for_episode(
        episode_id, episode_repo, series_repo, ProjectRole.VIEWER, user, membership_repo
    )
    return await service.get_drop_points(episode_id)


@router.get("/series/{series_id}/story-performance", response_model=list[StoryPerformanceInsight])
async def get_story_performance(
    series_id: str,
    service: StoryPerformanceLearningService = Depends(get_story_performance_service),
    series_repo: SeriesRepository = Depends(get_series_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> list[StoryPerformanceInsight]:
    """See MODULE-063 - suppresses any segment below the sample-size
    threshold; an empty list means "not enough data yet," not "no
    pattern.\""""
    series = await series_repo.get_series(series_id)
    if series is None:
        raise HTTPException(status_code=404, detail="series not found")
    await authorize_project_access(series.project_id, ProjectRole.VIEWER, user, membership_repo)
    return await service.analyze_series(series_id)
