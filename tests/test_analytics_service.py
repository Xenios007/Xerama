from datetime import datetime, timezone

from xerama.domain.asset import AssetOwnership, AssetProvenance, AssetStatus, AssetType
from xerama.domain.enums import CliffhangerType
from xerama.domain.episode import Cliffhanger, EpisodeOutline
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyAssetRepository,
    SQLAlchemyCostRecordRepository,
    SQLAlchemyEpisodeRepository,
    SQLAlchemyHumanFeedbackRepository,
    SQLAlchemyMediaQCRepository,
    SQLAlchemyMetricsRepository,
    SQLAlchemySeriesRepository,
)
from xerama.services.analytics_service import (
    AnalyticsIngestionService,
    RetentionAnalyticsService,
    StoryPerformanceLearningService,
)
from xerama.services.feedback_service import HumanFeedbackService
from xerama.services.optimization_service import OptimizationService

from test_repositories import _brief, _candidate
from test_storyboard_repository import _episode


def _window() -> tuple[datetime, datetime]:
    return (
        datetime(2026, 8, 1, tzinfo=timezone.utc),
        datetime(2026, 8, 8, tzinfo=timezone.utc),
    )


async def test_analytics_ingestion_service_normalizes_and_persists(session) -> None:
    episode_id = await _episode(session)
    service = AnalyticsIngestionService(repo=SQLAlchemyMetricsRepository(session))
    start, end = _window()

    metric = await service.import_metrics(
        episode_id, 1, "manual_import", start, end, {"views": 500, "completion_rate": 0.7}
    )
    await session.commit()

    assert metric.views == 500
    assert metric.completion_rate == 0.7

    listed = await service.list_metrics(episode_id)
    assert len(listed) == 1


async def test_retention_service_summarizes_from_ingested_metrics(session) -> None:
    episode_id = await _episode(session)
    ingestion = AnalyticsIngestionService(repo=SQLAlchemyMetricsRepository(session))
    start, end = _window()
    await ingestion.import_metrics(episode_id, 1, "manual_import", start, end, {"completion_rate": 0.6})
    await session.commit()

    retention = RetentionAnalyticsService(
        metrics_repo=SQLAlchemyMetricsRepository(session),
        episode_repo=SQLAlchemyEpisodeRepository(session),
    )
    summary = await retention.get_summary(episode_id)
    assert summary.sample_count == 1
    assert summary.avg_completion_rate == 0.6


async def _series_with_committed_episodes(session, count: int, cliffhanger: CliffhangerType) -> tuple[str, list[str]]:
    from xerama.repositories.sqlalchemy_impl import SQLAlchemyProjectRepository

    project = await SQLAlchemyProjectRepository(session).create("p")
    series_repo = SQLAlchemySeriesRepository(session)
    series = await series_repo.create_series(project.id, _brief(), _candidate("T"))
    episode_repo = SQLAlchemyEpisodeRepository(session)
    episode_ids = []
    for n in range(1, count + 1):
        record = await episode_repo.save_outline(
            series.id,
            EpisodeOutline(
                episode_number=n,
                objective="x", opening_hook="x", stakes="x", conflict="x",
                turn="x", reveal="x", duration_target_seconds=75,
                cliffhanger=Cliffhanger(type=cliffhanger, event="x"),
            ),
        )
        episode_ids.append(record.id)
    await session.commit()
    return series.id, episode_ids


async def test_story_performance_service_surfaces_pattern_with_enough_samples(session) -> None:
    series_id, episode_ids = await _series_with_committed_episodes(session, 3, CliffhangerType.THREAT)
    ingestion = AnalyticsIngestionService(repo=SQLAlchemyMetricsRepository(session))
    start, end = _window()
    for episode_id in episode_ids:
        await ingestion.import_metrics(episode_id, 1, "manual_import", start, end, {"completion_rate": 0.7})
    await session.commit()

    service = StoryPerformanceLearningService(
        metrics_repo=SQLAlchemyMetricsRepository(session),
        episode_repo=SQLAlchemyEpisodeRepository(session),
    )
    insights = await service.analyze_series(series_id)
    assert len(insights) == 1
    assert insights[0].segment == "threat"
    assert insights[0].sample_count == 3


async def test_story_performance_service_suppresses_below_threshold(session) -> None:
    series_id, episode_ids = await _series_with_committed_episodes(session, 2, CliffhangerType.THREAT)
    ingestion = AnalyticsIngestionService(repo=SQLAlchemyMetricsRepository(session))
    start, end = _window()
    for episode_id in episode_ids:
        await ingestion.import_metrics(episode_id, 1, "manual_import", start, end, {"completion_rate": 0.7})
    await session.commit()

    service = StoryPerformanceLearningService(
        metrics_repo=SQLAlchemyMetricsRepository(session),
        episode_repo=SQLAlchemyEpisodeRepository(session),
    )
    assert await service.analyze_series(series_id) == []


async def test_optimization_service_ranks_from_real_cost_and_qc_data(session) -> None:
    asset_repo = SQLAlchemyAssetRepository(session)
    asset = await asset_repo.create(
        asset_type=AssetType.IMAGE, storage_path="a.png", content_hash="h1",
        ownership=AssetOwnership(project_id="P1"),
        provenance=AssetProvenance(provider="reliable", model="m1"),
    )
    await asset_repo.set_status(asset.id, AssetStatus.ACCEPTED)
    cost_repo = SQLAlchemyCostRecordRepository(session)
    await cost_repo.create(
        provider="reliable", model="m1", stage="image_generation", project_id="P1",
        asset_id=asset.id, cost_usd=0.02, cost_known=True, latency_ms=800, unit="images",
    )
    qc_repo = SQLAlchemyMediaQCRepository(session)
    from xerama.domain.enums import MediaQCDimension, QCStatus

    await qc_repo.create(
        asset_id=asset.id, dimension=MediaQCDimension.COMPOSITION, status=QCStatus.PASS,
        score=9.0, evidence={}, reasons=[],
    )
    await session.commit()

    service = OptimizationService(cost_repo=cost_repo, qc_repo=qc_repo, asset_repo=asset_repo)
    rankings = await service.rank_providers("P1", objective="quality")
    assert len(rankings) == 1
    assert rankings[0].provider == "reliable"
    assert rankings[0].avg_qc_score == 9.0
    assert rankings[0].accepted_rate == 1.0


async def test_feedback_service_denormalizes_provider_and_model(session) -> None:
    asset_repo = SQLAlchemyAssetRepository(session)
    asset = await asset_repo.create(
        asset_type=AssetType.IMAGE, storage_path="a.png", content_hash="h1",
        ownership=AssetOwnership(project_id="P1"),
        provenance=AssetProvenance(provider="fake_image", model="m1"),
    )
    await session.commit()

    service = HumanFeedbackService(repo=SQLAlchemyHumanFeedbackRepository(session), asset_repo=asset_repo)
    feedback = await service.record(asset.id, "rejected", reason="blurry", rating=2, tags=["quality"])
    await session.commit()

    assert feedback.provider == "fake_image"
    assert feedback.model == "m1"
    assert feedback.project_id == "P1"

    by_project = await service.list_by_project("P1")
    assert len(by_project) == 1
