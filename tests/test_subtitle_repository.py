from xerama.repositories.sqlalchemy_impl import SQLAlchemySubtitleCueRepository

from test_storyboard_repository import _episode


def _cue_dict(**overrides) -> dict:
    base = dict(
        scene_number=1,
        shot_number=1,
        character_id="CHAR_001",
        text="hello",
        lines=["hello"],
        start_seconds=0.0,
        end_seconds=2.0,
    )
    base.update(overrides)
    return base


async def test_replace_track_inserts_cues(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemySubtitleCueRepository(session)

    cues = await repo.replace_track(episode_id, "en", [_cue_dict()])
    await session.commit()
    assert len(cues) == 1

    listed = await repo.list_by_episode(episode_id, "en")
    assert len(listed) == 1
    assert listed[0].text == "hello"


async def test_replace_track_is_idempotent_not_additive(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemySubtitleCueRepository(session)

    await repo.replace_track(episode_id, "en", [_cue_dict(shot_number=1)])
    await session.commit()
    await repo.replace_track(episode_id, "en", [_cue_dict(shot_number=2), _cue_dict(shot_number=3)])
    await session.commit()

    listed = await repo.list_by_episode(episode_id, "en")
    assert len(listed) == 2  # not 3 - old track was replaced, not appended to


async def test_replace_track_scopes_by_language(session) -> None:
    episode_id = await _episode(session)
    repo = SQLAlchemySubtitleCueRepository(session)

    await repo.replace_track(episode_id, "en", [_cue_dict()])
    await repo.replace_track(episode_id, "es", [_cue_dict(text="hola", lines=["hola"])])
    await session.commit()

    en_cues = await repo.list_by_episode(episode_id, "en")
    es_cues = await repo.list_by_episode(episode_id, "es")
    assert len(en_cues) == 1
    assert len(es_cues) == 1
    assert es_cues[0].text == "hola"


async def test_get_returns_none_for_unknown(session) -> None:
    repo = SQLAlchemySubtitleCueRepository(session)
    assert await repo.get("does-not-exist") is None
