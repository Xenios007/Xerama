"""Performance analytics endpoints (MODULE-061/062/063)."""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from xerama.api.deps import get_analytics_service, get_retention_service, get_story_performance_service
from xerama.domain.analytics import EpisodeMetric
from xerama.pipeline.retention_analytics import RetentionSummary, ShotDropPoint
from xerama.pipeline.story_performance import StoryPerformanceInsight
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


@router.post("/episodes/{episode_id}/metrics/import", response_model=EpisodeMetric)
async def import_episode_metrics(
    episode_id: str,
    body: ImportMetricsRequest,
    service: AnalyticsIngestionService = Depends(get_analytics_service),
) -> EpisodeMetric:
    """See MODULE-061 - the manual/import adapter; re-posting the same
    (render_version, source, window) updates that row (deduplication)."""
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
    episode_id: str, service: AnalyticsIngestionService = Depends(get_analytics_service)
) -> list[EpisodeMetric]:
    return await service.list_metrics(episode_id)


@router.get("/episodes/{episode_id}/retention-summary", response_model=RetentionSummary)
async def get_retention_summary(
    episode_id: str, service: RetentionAnalyticsService = Depends(get_retention_service)
) -> RetentionSummary:
    return await service.get_summary(episode_id)


@router.get("/episodes/{episode_id}/retention-drop-points", response_model=list[ShotDropPoint])
async def get_retention_drop_points(
    episode_id: str, service: RetentionAnalyticsService = Depends(get_retention_service)
) -> list[ShotDropPoint]:
    return await service.get_drop_points(episode_id)


@router.get("/series/{series_id}/story-performance", response_model=list[StoryPerformanceInsight])
async def get_story_performance(
    series_id: str, service: StoryPerformanceLearningService = Depends(get_story_performance_service)
) -> list[StoryPerformanceInsight]:
    """See MODULE-063 - suppresses any segment below the sample-size
    threshold; an empty list means "not enough data yet," not "no
    pattern.\""""
    return await service.analyze_series(series_id)
