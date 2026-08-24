import pytest

from xerama.domain.rights import RightsMetadata
from xerama.repositories.sqlalchemy_impl import SQLAlchemyMusicCueRepository
from xerama.services.music_cue_service import CueNotReadyError, MusicCueService

from test_storyboard_repository import _episode


def _service(session) -> MusicCueService:
    return MusicCueService(repo=SQLAlchemyMusicCueRepository(session))


async def test_create_cue(session) -> None:
    episode_id = await _episode(session)
    service = _service(session)
    cue = await service.create_cue(episode_id, "tension build", "dread", 0.0, 10.0)
    await session.commit()
    assert cue.status == "draft"


async def test_approve_requires_linked_asset(session) -> None:
    episode_id = await _episode(session)
    service = _service(session)
    cue = await service.create_cue(episode_id, "p", "m", 0.0, 5.0)
    await session.commit()

    with pytest.raises(CueNotReadyError):
        await service.approve_cue(cue.id)


async def test_approve_requires_known_rights(session) -> None:
    episode_id = await _episode(session)
    service = _service(session)
    cue = await service.create_cue(episode_id, "p", "m", 0.0, 5.0)
    await session.commit()
    await service.link_asset(cue.id, "asset-1", RightsMetadata(license_type="unknown"))
    await session.commit()

    with pytest.raises(PermissionError):
        await service.approve_cue(cue.id)


async def test_approve_succeeds_with_asset_and_known_rights(session) -> None:
    episode_id = await _episode(session)
    service = _service(session)
    cue = await service.create_cue(episode_id, "p", "m", 0.0, 5.0)
    await session.commit()
    await service.link_asset(cue.id, "asset-1", RightsMetadata(license_type="royalty_free"))
    await session.commit()

    approved = await service.approve_cue(cue.id)
    await session.commit()
    assert approved.status == "approved"


async def test_relinking_asset_resets_approval_to_draft(session) -> None:
    episode_id = await _episode(session)
    service = _service(session)
    cue = await service.create_cue(episode_id, "p", "m", 0.0, 5.0)
    await session.commit()
    await service.link_asset(cue.id, "asset-1", RightsMetadata(license_type="royalty_free"))
    await session.commit()
    await service.approve_cue(cue.id)
    await session.commit()

    relinked = await service.link_asset(cue.id, "asset-2", RightsMetadata(license_type="royalty_free"))
    await session.commit()
    assert relinked.status == "draft"


async def test_delete_cue(session) -> None:
    episode_id = await _episode(session)
    service = _service(session)
    cue = await service.create_cue(episode_id, "p", "m", 0.0, 5.0)
    await session.commit()

    await service.delete_cue(cue.id)
    await session.commit()
    with pytest.raises(ValueError):
        await service.get(cue.id)
