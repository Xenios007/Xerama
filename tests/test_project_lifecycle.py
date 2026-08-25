import pytest

from xerama.domain.brief import CreativeBrief
from xerama.domain.story import ConceptCandidate, Protagonist
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyEpisodeRenderRepository,
    SQLAlchemyEpisodeRepository,
    SQLAlchemyProjectRepository,
    SQLAlchemySeriesRepository,
)


def _candidate() -> ConceptCandidate:
    return ConceptCandidate(
        title="T",
        genre=["thriller"],
        logline="logline",
        premise="premise",
        protagonist=Protagonist(name="Mara", role="protagonist", desire="truth", flaw="pride"),
        antagonistic_force="family",
        central_conflict="loyalty vs. justice",
        central_secret="secret",
        emotional_engine="betrayal",
        opening_hook="hook",
        serial_engine="engine",
        ending_direction="direction",
    )


async def test_list_all_returns_every_project_newest_first(session) -> None:
    repo = SQLAlchemyProjectRepository(session)
    first = await repo.create("First")
    await session.commit()
    second = await repo.create("Second")
    await session.commit()

    projects = await repo.list_all()
    assert [p.id for p in projects][:2] == [second.id, first.id]


async def test_update_changes_name_and_description(session) -> None:
    repo = SQLAlchemyProjectRepository(session)
    project = await repo.create("Original", "desc")
    await session.commit()

    updated = await repo.update(project.id, name="Renamed")
    await session.commit()
    assert updated.name == "Renamed"
    assert updated.description == "desc"  # untouched field preserved


async def test_update_unknown_project_raises_value_error(session) -> None:
    repo = SQLAlchemyProjectRepository(session)
    with pytest.raises(ValueError):
        await repo.update("does-not-exist", name="x")


async def test_archive_then_update_is_rejected(session) -> None:
    repo = SQLAlchemyProjectRepository(session)
    project = await repo.create("P")
    await session.commit()

    archived = await repo.archive(project.id)
    await session.commit()
    assert archived.status == "archived"

    with pytest.raises(PermissionError):
        await repo.update(project.id, name="new name")


async def test_archive_is_idempotent(session) -> None:
    repo = SQLAlchemyProjectRepository(session)
    project = await repo.create("P")
    await session.commit()
    await repo.archive(project.id)
    await session.commit()
    twice = await repo.archive(project.id)
    assert twice.status == "archived"


async def test_series_list_by_project(session) -> None:
    project_repo = SQLAlchemyProjectRepository(session)
    series_repo = SQLAlchemySeriesRepository(session)
    project = await project_repo.create("P")
    brief = CreativeBrief(genre="thriller", episode_count=3, episode_duration_seconds=75)
    await series_repo.create_series(project.id, brief, _candidate())
    await series_repo.create_series(project.id, brief, _candidate())
    await session.commit()

    series_list = await series_repo.list_by_project(project.id)
    assert len(series_list) == 2


async def test_episode_render_repo_get_current_none_when_no_render(session) -> None:
    repo = SQLAlchemyEpisodeRenderRepository(session)
    assert await repo.get_current("does-not-exist") is None
