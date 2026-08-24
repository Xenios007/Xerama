from xerama.repositories.sqlalchemy_impl import SQLAlchemyVoiceProfileRepository

from test_character_casting_repository import _character


async def test_get_or_create_is_idempotent(session) -> None:
    _, character_id = await _character(session)
    repo = SQLAlchemyVoiceProfileRepository(session)

    first = await repo.get_or_create(character_id)
    await session.commit()
    second = await repo.get_or_create(character_id)
    assert first.id == second.id


async def test_save_persists_fields(session) -> None:
    _, character_id = await _character(session)
    repo = SQLAlchemyVoiceProfileRepository(session)
    profile = await repo.get_or_create(character_id)
    await session.commit()

    profile.provider = "fake_voice"
    profile.provider_voice_id = "voice-42"
    profile.language = "es"
    profile.pronunciation_dictionary = {"Mara": "MAH-rah"}
    saved = await repo.save(profile)
    await session.commit()

    assert saved.provider_voice_id == "voice-42"
    refetched = await repo.get_or_create(character_id)
    assert refetched.language == "es"
    assert refetched.pronunciation_dictionary == {"Mara": "MAH-rah"}


async def test_set_lock_and_unlock_and_bump_version(session) -> None:
    _, character_id = await _character(session)
    repo = SQLAlchemyVoiceProfileRepository(session)
    await repo.get_or_create(character_id)
    await session.commit()

    locked = await repo.set_lock(character_id, True)
    assert locked.locked is True
    assert locked.version == 1

    unlocked = await repo.unlock_and_bump_version(character_id)
    await session.commit()
    assert unlocked.locked is False
    assert unlocked.version == 2
