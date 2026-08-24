import pytest

from xerama.repositories.sqlalchemy_impl import SQLAlchemyProjectRepository, SQLAlchemySeriesRepository, SQLAlchemyStyleBibleRepository

from test_repositories import _brief, _candidate


async def _series(session) -> str:
    project = await SQLAlchemyProjectRepository(session).create("p")
    series = await SQLAlchemySeriesRepository(session).create_series(project.id, _brief(), _candidate("T"))
    await session.commit()
    return series.id


async def test_get_or_create_is_idempotent(session) -> None:
    series_id = await _series(session)
    repo = SQLAlchemyStyleBibleRepository(session)

    first = await repo.get_or_create(series_id)
    await session.commit()
    second = await repo.get_or_create(series_id)
    assert first.id == second.id


async def test_save_persists_fields(session) -> None:
    series_id = await _series(session)
    repo = SQLAlchemyStyleBibleRepository(session)
    style_bible = await repo.get_or_create(series_id)
    await session.commit()

    style_bible.style_dna = "high-contrast neon noir"
    style_bible.palette = ["#101018", "#ff2e63"]
    style_bible.negatives = ["oversaturated pastel"]
    saved = await repo.save(style_bible)
    await session.commit()

    assert saved.style_dna == "high-contrast neon noir"
    refetched = await repo.get_or_create(series_id)
    assert refetched.palette == ["#101018", "#ff2e63"]


async def test_save_raises_for_unknown_style_bible(session) -> None:
    from xerama.domain.style_bible import StyleBible

    repo = SQLAlchemyStyleBibleRepository(session)
    with pytest.raises(ValueError):
        await repo.save(StyleBible(id="does-not-exist", series_id="SER_X"))


async def test_set_lock_and_unlock_and_bump_version(session) -> None:
    series_id = await _series(session)
    repo = SQLAlchemyStyleBibleRepository(session)
    await repo.get_or_create(series_id)
    await session.commit()

    locked = await repo.set_lock(series_id, True)
    assert locked.locked is True
    assert locked.version == 1

    unlocked = await repo.unlock_and_bump_version(series_id)
    await session.commit()
    assert unlocked.locked is False
    assert unlocked.version == 2
