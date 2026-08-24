import pytest

from xerama.domain.rights import RightsMetadata
from xerama.repositories.sqlalchemy_impl import SQLAlchemySoundEffectCueRepository

from test_storyboard_repository import _episode


async def test_create_and_get_round_trip(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemySoundEffectCueRepository(session)
    cue = await repo.create(episode_id, 1, "door slams", 0.0, 1.0, shot_number=1, gain_db=-3.0)
    await session.commit()

    fetched = await repo.get(cue.id)
    assert fetched is not None
    assert fetched.description == "door slams"
    assert fetched.gain_db == -3.0
    assert fetched.status == "draft"


async def test_update_persists_fields(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemySoundEffectCueRepository(session)
    cue = await repo.create(episode_id, 1, "d", 0.0, 1.0)
    await session.commit()

    cue.asset_id = "asset-1"
    cue.rights = RightsMetadata(license_type="cc0")
    cue.status = "approved"
    updated = await repo.update(cue)
    await session.commit()

    assert updated.asset_id == "asset-1"
    assert updated.status == "approved"


async def test_update_raises_for_unknown_cue(session) -> None:
    from xerama.domain.sound_effect import SoundEffectCue

    repo = SQLAlchemySoundEffectCueRepository(session)
    with pytest.raises(ValueError):
        await repo.update(
            SoundEffectCue(id="does-not-exist", episode_id="EP_1", scene_number=1, start_seconds=0.0, end_seconds=1.0)
        )


async def test_delete_removes_row(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemySoundEffectCueRepository(session)
    cue = await repo.create(episode_id, 1, "d", 0.0, 1.0)
    await session.commit()

    await repo.delete(cue.id)
    await session.commit()
    assert await repo.get(cue.id) is None


async def test_list_by_episode_ordered_by_start(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemySoundEffectCueRepository(session)
    await repo.create(episode_id, 1, "second", 5.0, 6.0)
    await repo.create(episode_id, 1, "first", 0.0, 1.0)
    await session.commit()

    cues = await repo.list_by_episode(episode_id)
    assert [c.description for c in cues] == ["first", "second"]
