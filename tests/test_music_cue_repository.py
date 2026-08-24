import pytest

from xerama.domain.rights import RightsMetadata
from xerama.repositories.sqlalchemy_impl import SQLAlchemyMusicCueRepository

from test_storyboard_repository import _episode


async def test_create_and_get_round_trip(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyMusicCueRepository(session)
    cue = await repo.create(episode_id, "tension build", "dread", 0.0, 10.0, ducking_db=-6.0, scene_number=1)
    await session.commit()

    fetched = await repo.get(cue.id)
    assert fetched is not None
    assert fetched.purpose == "tension build"
    assert fetched.ducking_db == -6.0
    assert fetched.status == "draft"


async def test_update_persists_fields(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyMusicCueRepository(session)
    cue = await repo.create(episode_id, "p", "m", 0.0, 5.0)
    await session.commit()

    cue.asset_id = "asset-1"
    cue.rights = RightsMetadata(license_type="royalty_free")
    cue.status = "approved"
    updated = await repo.update(cue)
    await session.commit()

    assert updated.asset_id == "asset-1"
    assert updated.status == "approved"
    refetched = await repo.get(cue.id)
    assert refetched.rights.license_type == "royalty_free"


async def test_update_raises_for_unknown_cue(session) -> None:
    from xerama.domain.music import MusicCue

    repo = SQLAlchemyMusicCueRepository(session)
    with pytest.raises(ValueError):
        await repo.update(MusicCue(id="does-not-exist", episode_id="EP_1", start_seconds=0.0, end_seconds=1.0))


async def test_delete_removes_row(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyMusicCueRepository(session)
    cue = await repo.create(episode_id, "p", "m", 0.0, 5.0)
    await session.commit()

    await repo.delete(cue.id)
    await session.commit()
    assert await repo.get(cue.id) is None


async def test_list_by_episode_ordered_by_start(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemyMusicCueRepository(session)
    await repo.create(episode_id, "p2", "m", 10.0, 20.0)
    await repo.create(episode_id, "p1", "m", 0.0, 5.0)
    await session.commit()

    cues = await repo.list_by_episode(episode_id)
    assert [c.purpose for c in cues] == ["p1", "p2"]
