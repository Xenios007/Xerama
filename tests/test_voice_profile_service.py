import pytest

from xerama.repositories.sqlalchemy_impl import SQLAlchemyVoiceProfileRepository
from xerama.services.voice_profile_service import VoiceProfileService

from test_character_casting_repository import _character


def _service(session) -> VoiceProfileService:
    return VoiceProfileService(repo=SQLAlchemyVoiceProfileRepository(session))


async def test_update_when_unlocked(session) -> None:
    _, character_id = await _character(session)
    service = _service(session)

    updated = await service.update(character_id, provider="fake_voice", provider_voice_id="v1")
    await session.commit()
    assert updated.provider_voice_id == "v1"


async def test_locked_voice_profile_is_immutable(session) -> None:
    _, character_id = await _character(session)
    service = _service(session)

    await service.lock(character_id)
    await session.commit()

    with pytest.raises(PermissionError):
        await service.update(character_id, provider="anything")


async def test_unlock_for_recast_allows_update_and_bumps_version(session) -> None:
    _, character_id = await _character(session)
    service = _service(session)

    await service.lock(character_id)
    await session.commit()

    recast = await service.unlock_for_recast(character_id)
    await session.commit()
    assert recast.locked is False
    assert recast.version == 2

    updated = await service.update(character_id, provider_voice_id="v2")
    assert updated.provider_voice_id == "v2"
