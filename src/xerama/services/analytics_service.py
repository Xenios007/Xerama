"""Analytics ingestion, retention analytics, and story performance
learning (MODULE-061/062/063).

Built together - 062 and 063 are pure read/aggregate layers over 061's
ingested `EpisodeMetric` rows, so splitting them into separate services
would just mean threading the same repository through three files.
"""

from datetime import datetime

from xerama.domain.analytics import EpisodeMetric
from xerama.pipeline.metrics_normalization import normalize_manual_payload
from xerama.pipeline.retention_analytics import (
    RetentionSummary,
    ShotDropPoint,
    map_drop_points_to_shots,
    summarize_retention,
)
from xerama.pipeline.story_performance import StoryPerformanceInsight, analyze_cliffhanger_performance
from xerama.repositories.interfaces import EpisodeRepository, MetricsRepository


class AnalyticsIngestionService:
    """MODULE-061."""

    def __init__(self, repo: MetricsRepository) -> None:
        self._repo = repo

    async def import_metrics(
        self,
        episode_id: str,
        render_version: int,
        source: str,
        observation_window_start: datetime,
        observation_window_end: datetime,
        payload: dict,
    ) -> EpisodeMetric:
        normalized = normalize_manual_payload(payload)
        return await self._repo.upsert(
            episode_id=episode_id,
            render_version=render_version,
            source=source,
            observation_window_start=observation_window_start,
            observation_window_end=observation_window_end,
            raw_payload=payload,
            **normalized,
        )

    async def list_metrics(self, episode_id: str) -> list[EpisodeMetric]:
        return await self._repo.list_by_episode(episode_id)


class RetentionAnalyticsService:
    """MODULE-062."""

    def __init__(self, metrics_repo: MetricsRepository, episode_repo: EpisodeRepository) -> None:
        self._metrics_repo = metrics_repo
        self._episode_repo = episode_repo

    async def get_summary(self, episode_id: str) -> RetentionSummary:
        metrics = await self._metrics_repo.list_by_episode(episode_id)
        return summarize_retention(episode_id, metrics)

    async def get_drop_points(self, episode_id: str) -> list[ShotDropPoint]:
        metrics = await self._metrics_repo.list_by_episode(episode_id)
        plan = await self._episode_repo.get_shot_plan(episode_id)
        if plan is None:
            return []
        return map_drop_points_to_shots(metrics, plan)


class StoryPerformanceLearningService:
    """MODULE-063."""

    def __init__(self, metrics_repo: MetricsRepository, episode_repo: EpisodeRepository) -> None:
        self._metrics_repo = metrics_repo
        self._episode_repo = episode_repo

    async def analyze_series(self, series_id: str) -> list[StoryPerformanceInsight]:
        episodes = await self._episode_repo.list_by_series(series_id)
        episode_cliffhangers = [
            (episode.id, episode.outline.cliffhanger.type) for episode in episodes
        ]
        summaries_by_episode = {}
        for episode in episodes:
            metrics = await self._metrics_repo.list_by_episode(episode.id)
            summaries_by_episode[episode.id] = summarize_retention(episode.id, metrics)
        return analyze_cliffhanger_performance(episode_cliffhangers, summaries_by_episode)
