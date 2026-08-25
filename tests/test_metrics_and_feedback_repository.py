from datetime import datetime, timezone

from xerama.domain.asset import AssetOwnership, AssetProvenance, AssetType
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyAssetRepository,
    SQLAlchemyHumanFeedbackRepository,
    SQLAlchemyMetricsRepository,
)

from test_storyboard_repository import _episode


def _window() -> tuple[datetime, datetime]:
    return (
        datetime(2026, 8, 1, tzinfo=timezone.utc),
        datetime(2026, 8, 8, tzinfo=timezone.utc),
    )


async def test_metrics_upsert_is_idempotent_on_the_same_window(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyMetricsRepository(session)
    start, end = _window()

    first = await repo.upsert(
        episode_id, render_version=1, source="manual_import",
        observation_window_start=start, observation_window_end=end,
        raw_payload={"views": 100}, views=100,
    )
    await session.commit()
    second = await repo.upsert(
        episode_id, render_version=1, source="manual_import",
        observation_window_start=start, observation_window_end=end,
        raw_payload={"views": 250}, views=250,
    )
    await session.commit()

    assert first.id == second.id  # same row updated, not duplicated
    rows = await repo.list_by_episode(episode_id)
    assert len(rows) == 1
    assert rows[0].views == 250


async def test_metrics_upsert_creates_separate_rows_for_different_sources(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyMetricsRepository(session)
    start, end = _window()

    await repo.upsert(
        episode_id, render_version=1, source="manual_import",
        observation_window_start=start, observation_window_end=end, raw_payload={},
    )
    await repo.upsert(
        episode_id, render_version=1, source="tiktok_import",
        observation_window_start=start, observation_window_end=end, raw_payload={},
    )
    await session.commit()

    rows = await repo.list_by_episode(episode_id)
    assert len(rows) == 2


async def test_metrics_preserves_raw_payload(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyMetricsRepository(session)
    start, end = _window()
    raw = {"views": 100, "platform_specific_field": "xyz"}

    await repo.upsert(
        episode_id, render_version=1, source="manual_import",
        observation_window_start=start, observation_window_end=end,
        raw_payload=raw, views=100,
    )
    await session.commit()

    rows = await repo.list_by_episode(episode_id)
    assert rows[0].raw_payload == raw


async def test_human_feedback_create_and_list(session) -> None:
    asset_repo = SQLAlchemyAssetRepository(session)
    asset = await asset_repo.create(
        asset_type=AssetType.IMAGE,
        storage_path="a.png",
        content_hash="h1",
        ownership=AssetOwnership(project_id="P1"),
        provenance=AssetProvenance(provider="fake_image", model="m1"),
    )
    await session.commit()

    repo = SQLAlchemyHumanFeedbackRepository(session)
    await repo.create(
        asset.id, "rejected", project_id="P1", reason="face looks off",
        rating=2, tags=["identity"], reviewer="alice",
        provider="fake_image", model="m1",
    )
    await repo.create(asset.id, "approved", project_id="P1", rating=5)
    await session.commit()

    by_asset = await repo.list_by_asset(asset.id)
    assert len(by_asset) == 2
    assert by_asset[0].decision == "rejected"
    assert by_asset[0].tags == ["identity"]

    by_project = await repo.list_by_project("P1")
    assert len(by_project) == 2
