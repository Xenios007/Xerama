from xerama.domain.enums import AudioMode
from xerama.repositories.sqlalchemy_impl import SQLAlchemyAudioProductionRepository

from test_storyboard_repository import _episode


async def test_get_or_create_is_idempotent_per_shot(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyAudioProductionRepository(session)

    first = await repo.get_or_create(episode_id, 1, 1, audio_mode=AudioMode.TTS_LIPSYNC)
    await session.commit()
    second = await repo.get_or_create(episode_id, 1, 1)
    assert first.id == second.id
    assert second.audio_mode == AudioMode.TTS_LIPSYNC

    other_shot = await repo.get_or_create(episode_id, 1, 2)
    assert other_shot.id != first.id
    assert other_shot.audio_mode == AudioMode.NATIVE


async def test_get_returns_none_for_unknown(session) -> None:
    repo = SQLAlchemyAudioProductionRepository(session)
    assert await repo.get("does-not-exist") is None


async def test_approve_sets_status_and_approved_asset(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyAudioProductionRepository(session)
    production = await repo.get_or_create(episode_id, 1, 1)
    await session.commit()

    approved = await repo.approve(production.id, "asset-123")
    await session.commit()
    assert approved.status == "approved"
    assert approved.approved_take_asset_id == "asset-123"


async def test_list_by_episode(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyAudioProductionRepository(session)
    await repo.get_or_create(episode_id, 1, 1)
    await repo.get_or_create(episode_id, 1, 2)
    await session.commit()

    productions = await repo.list_by_episode(episode_id)
    assert len(productions) == 2
