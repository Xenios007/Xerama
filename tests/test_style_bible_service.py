import pytest

from xerama.repositories.sqlalchemy_impl import SQLAlchemyStyleBibleRepository
from xerama.services.style_bible_service import StyleBibleService

from test_style_bible_repository import _series


def _service(session) -> StyleBibleService:
    return StyleBibleService(repo=SQLAlchemyStyleBibleRepository(session))


async def test_update_when_unlocked(session) -> None:
    series_id = await _series(session)
    service = _service(session)

    updated = await service.update(series_id, style_dna="neon noir", palette=["#000", "#f00"])
    await session.commit()

    assert updated.style_dna == "neon noir"
    assert updated.palette == ["#000", "#f00"]


async def test_locked_style_bible_is_immutable(session) -> None:
    series_id = await _series(session)
    service = _service(session)

    await service.lock(series_id)
    await session.commit()

    with pytest.raises(PermissionError):
        await service.update(series_id, style_dna="anything")


async def test_unlock_for_recast_allows_update_and_bumps_version(session) -> None:
    series_id = await _series(session)
    service = _service(session)

    await service.lock(series_id)
    await session.commit()

    recast = await service.unlock_for_recast(series_id)
    await session.commit()
    assert recast.locked is False
    assert recast.version == 2

    updated = await service.update(series_id, style_dna="v2 style")
    assert updated.style_dna == "v2 style"
