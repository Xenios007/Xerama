import pytest

from xerama.domain.rights import RightsMetadata
from xerama.domain.scene import Shot
from xerama.repositories.sqlalchemy_impl import SQLAlchemySoundEffectCueRepository
from xerama.services.sound_effect_service import CueNotReadyError, SoundEffectCueService

from test_storyboard_repository import _episode


def _service(session) -> SoundEffectCueService:
    return SoundEffectCueService(repo=SQLAlchemySoundEffectCueRepository(session))


async def test_create_cue(session) -> None:
    episode_id = await _episode(session)
    service = _service(session)
    cue = await service.create_cue(episode_id, 1, "door slams", 0.0, 1.0)
    await session.commit()
    assert cue.status == "draft"


async def test_derive_candidates_for_shot_persists_draft_cues(session) -> None:
    episode_id = await _episode(session)
    service = _service(session)
    shot = Shot(
        shot_number=1, scene_number=1, duration_seconds=5.0, action="The door slams and glass breaks."
    )
    cues = await service.derive_candidates_for_shot(episode_id, 1, shot)
    await session.commit()

    assert len(cues) == 2
    assert {c.description for c in cues} == {"door slams", "glass breaks"}
    listed = await service.list_by_episode(episode_id)
    assert len(listed) == 2


async def test_approve_requires_linked_asset(session) -> None:
    episode_id = await _episode(session)
    service = _service(session)
    cue = await service.create_cue(episode_id, 1, "d", 0.0, 1.0)
    await session.commit()

    with pytest.raises(CueNotReadyError):
        await service.approve_cue(cue.id)


async def test_approve_requires_known_rights(session) -> None:
    episode_id = await _episode(session)
    service = _service(session)
    cue = await service.create_cue(episode_id, 1, "d", 0.0, 1.0)
    await session.commit()
    await service.link_asset(cue.id, "asset-1", RightsMetadata())
    await session.commit()

    with pytest.raises(PermissionError):
        await service.approve_cue(cue.id)


async def test_approve_succeeds_with_asset_and_known_rights(session) -> None:
    episode_id = await _episode(session)
    service = _service(session)
    cue = await service.create_cue(episode_id, 1, "d", 0.0, 1.0)
    await session.commit()
    await service.link_asset(cue.id, "asset-1", RightsMetadata(license_type="library_licensed"))
    await session.commit()

    approved = await service.approve_cue(cue.id)
    await session.commit()
    assert approved.status == "approved"
