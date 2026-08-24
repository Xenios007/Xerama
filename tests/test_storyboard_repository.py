from xerama.domain.enums import CliffhangerType
from xerama.domain.episode import Cliffhanger, EpisodeOutline
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyEpisodeRepository,
    SQLAlchemyProjectRepository,
    SQLAlchemySeriesRepository,
    SQLAlchemyStoryboardRepository,
)

from test_repositories import _brief, _candidate


async def _episode(session) -> str:
    project = await SQLAlchemyProjectRepository(session).create("p")
    series = await SQLAlchemySeriesRepository(session).create_series(project.id, _brief(), _candidate("T"))
    episode = await SQLAlchemyEpisodeRepository(session).save_outline(
        series.id,
        EpisodeOutline(
            episode_number=1,
            objective="find the truth",
            opening_hook="a scream",
            stakes="freedom",
            conflict="sister vs sister",
            turn="the letter was fake",
            reveal="he was never who he claimed",
            duration_target_seconds=75,
            cliffhanger=Cliffhanger(type=CliffhangerType.IDENTITY_REVEAL, event="the mask comes off"),
        ),
    )
    await session.commit()
    return episode.id


async def test_get_or_create_is_idempotent_per_shot(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyStoryboardRepository(session)

    first = await repo.get_or_create(episode_id, 1, 1, layout_description="wide establishing")
    await session.commit()
    second = await repo.get_or_create(episode_id, 1, 1)
    assert first.id == second.id
    assert second.layout_description == "wide establishing"

    other_shot = await repo.get_or_create(episode_id, 1, 2)
    assert other_shot.id != first.id


async def test_get_returns_none_for_unknown(session) -> None:
    repo = SQLAlchemyStoryboardRepository(session)
    assert await repo.get("does-not-exist") is None


async def test_approve_sets_status_and_approved_asset(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyStoryboardRepository(session)
    storyboard = await repo.get_or_create(episode_id, 1, 1)
    await session.commit()

    approved = await repo.approve(storyboard.id, "asset-123")
    await session.commit()
    assert approved.status == "approved"
    assert approved.approved_keyframe_asset_id == "asset-123"


async def test_list_by_episode(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyStoryboardRepository(session)
    await repo.get_or_create(episode_id, 1, 1)
    await repo.get_or_create(episode_id, 1, 2)
    await session.commit()

    storyboards = await repo.list_by_episode(episode_id)
    assert len(storyboards) == 2
