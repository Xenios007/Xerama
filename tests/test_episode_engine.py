import json

import pytest

import fixtures as fx
from test_repositories import _brief, _candidate
from xerama.config import ModelRoleRegistry, Settings
from xerama.domain.character import CharacterCast
from xerama.domain.enums import EpisodeGenerationStatus, QCStatus
from xerama.domain.episode import EpisodeOutline
from xerama.domain.story import SeriesBible
from xerama.pipeline.ai_gateway import AIGateway
from xerama.pipeline.episode_engine import EpisodeEngine
from xerama.providers.fake import FakeLLMProvider
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyEpisodeRepository,
    SQLAlchemyJobRepository,
    SQLAlchemyProjectRepository,
    SQLAlchemySeriesRepository,
)


def _outline(n: int, canon_changes: list[str] | None = None) -> dict:
    data = fx.outline(n)
    data["canon_changes"] = canon_changes or []
    return data


def _script(episode_number: int, line: str) -> dict:
    data = fx.script()
    data["episode_number"] = episode_number
    data["scenes"][0]["dialogue"][0]["line"] = line
    return data


def _broken_shot_plan() -> dict:
    plan = fx.shot_plan()
    plan["scenes"][0]["shots"][0]["character_ids"] = ["CHAR_999"]
    return plan


async def _setup_series(session, episode_canon_changes: dict[int, list[str]] | None = None):
    episode_canon_changes = episode_canon_changes or {}
    project = await SQLAlchemyProjectRepository(session).create("Trial 01")
    series_repo = SQLAlchemySeriesRepository(session)
    episode_repo = SQLAlchemyEpisodeRepository(session)

    series = await series_repo.create_series(project.id, _brief(), _candidate("T"))
    await series_repo.save_bible(series.id, SeriesBible.model_validate(fx.bible()))
    await series_repo.save_cast(series.id, CharacterCast.model_validate(fx.cast()))
    for n in (1, 2, 3):
        outline = EpisodeOutline.model_validate(_outline(n, episode_canon_changes.get(n)))
        await episode_repo.save_outline(series.id, outline)
    await session.commit()
    return project, series


def _engine(session, provider: FakeLLMProvider) -> EpisodeEngine:
    gateway = AIGateway(provider=provider, roles=ModelRoleRegistry(Settings()))
    return EpisodeEngine(
        gateway=gateway,
        series_repo=SQLAlchemySeriesRepository(session),
        episode_repo=SQLAlchemyEpisodeRepository(session),
        job_repo=SQLAlchemyJobRepository(session),
    )


@pytest.mark.asyncio
async def test_three_episode_serialization_with_evolving_canon(session) -> None:
    project, series = await _setup_series(
        session,
        {
            1: ["Mara finds the forged letter"],
            2: ["Lena's secret is exposed"],
            3: ["Mara confronts Lena"],
        },
    )
    provider = FakeLLMProvider(
        [
            json.dumps(_script(1, "Episode one line")),
            json.dumps(fx.shot_plan()),
            json.dumps(_script(2, "Episode two line")),
            json.dumps(fx.shot_plan()),
            json.dumps(_script(3, "Episode three line")),
            json.dumps(fx.shot_plan()),
        ]
    )
    engine = _engine(session, provider)

    result1 = await engine.generate_episode(project.id, series.id, 1)
    await session.commit()
    result2 = await engine.generate_episode(project.id, series.id, 2)
    await session.commit()
    result3 = await engine.generate_episode(project.id, series.id, 3)
    await session.commit()

    assert result1.canon_committed and result2.canon_committed and result3.canon_committed

    episode_repo = SQLAlchemyEpisodeRepository(session)
    episodes = await episode_repo.list_by_series(series.id)
    assert {e.status for e in episodes} == {EpisodeGenerationStatus.CANON_COMMITTED.value}

    # Episode 2's script prompt must include episode 1's committed canon
    # event - propagation through structured canon, not raw chat history.
    episode2_script_call = provider.calls[2]  # 0: ep1 script, 1: ep1 shots, 2: ep2 script
    assert "Mara finds the forged letter" in episode2_script_call.messages[-1].content

    episode3_script_call = provider.calls[4]
    assert "Mara finds the forged letter" in episode3_script_call.messages[-1].content
    assert "Lena's secret is exposed" in episode3_script_call.messages[-1].content


@pytest.mark.asyncio
async def test_blocked_episode_does_not_enter_canon(session) -> None:
    project, series = await _setup_series(session, {1: ["Mara finds the forged letter"]})
    provider = FakeLLMProvider(
        [
            json.dumps(_script(1, "Episode one line")),
            json.dumps(_broken_shot_plan()),
            json.dumps(_broken_shot_plan()),
        ]
    )
    engine = _engine(session, provider)

    result = await engine.generate_episode(project.id, series.id, 1)
    await session.commit()

    assert result.canon_committed is False
    assert result.continuity_qc.status == QCStatus.BLOCK

    episode_repo = SQLAlchemyEpisodeRepository(session)
    episode = await episode_repo.get(result.episode_id)
    assert episode.status == EpisodeGenerationStatus.QC_BLOCKED.value

    events = await episode_repo.list_canon_events(series.id)
    assert events == []


@pytest.mark.asyncio
async def test_generate_next_unfinished_retries_blocked_episode_not_skip_to_next(session) -> None:
    project, series = await _setup_series(session, {1: ["fact one"], 2: ["fact two"]})
    provider = FakeLLMProvider(
        [
            json.dumps(_script(1, "line one")),
            json.dumps(fx.shot_plan()),  # episode 1 succeeds
            json.dumps(_script(2, "line two")),
            json.dumps(_broken_shot_plan()),
            json.dumps(_broken_shot_plan()),  # episode 2 blocked
        ]
    )
    engine = _engine(session, provider)

    await engine.generate_next_unfinished(project.id, series.id)  # episode 1
    await session.commit()
    result = await engine.generate_next_unfinished(project.id, series.id)  # episode 2, blocked
    await session.commit()
    assert result.episode_number == 2
    assert result.canon_committed is False

    # Resume: episode 2 is still not committed, so the next call must retry
    # it rather than silently moving on to episode 3.
    provider.queue(json.dumps(_script(2, "line two retry")))
    provider.queue(json.dumps(fx.shot_plan()))
    resumed = await engine.generate_next_unfinished(project.id, series.id)
    await session.commit()
    assert resumed.episode_number == 2
    assert resumed.canon_committed is True


@pytest.mark.asyncio
async def test_regenerating_episode_marks_downstream_stale_and_replaces_canon(session) -> None:
    project, series = await _setup_series(
        session, {1: ["fact one"], 2: ["fact two"], 3: ["fact three"]}
    )
    provider = FakeLLMProvider(
        [
            json.dumps(_script(1, "line one")),
            json.dumps(fx.shot_plan()),
            json.dumps(_script(2, "line two")),
            json.dumps(fx.shot_plan()),
            json.dumps(_script(3, "line three")),
            json.dumps(fx.shot_plan()),
        ]
    )
    engine = _engine(session, provider)
    for n in (1, 2, 3):
        await engine.generate_episode(project.id, series.id, n)
        await session.commit()

    episode_repo = SQLAlchemyEpisodeRepository(session)
    episode1 = await episode_repo.get_by_number(series.id, 1)
    assert episode1.version == 1

    # Regenerate episode 1 with a different fact.
    provider.queue(json.dumps(_script(1, "line one, revised")))
    provider.queue(json.dumps(fx.shot_plan()))
    await engine.generate_episode(project.id, series.id, 1)
    await session.commit()

    episodes = {e.episode_number: e for e in await episode_repo.list_by_series(series.id)}
    assert episodes[1].status == EpisodeGenerationStatus.CANON_COMMITTED.value
    assert episodes[1].version == 2
    assert episodes[2].status == EpisodeGenerationStatus.STALE.value
    assert episodes[3].status == EpisodeGenerationStatus.STALE.value

    # Regeneration re-commits the same outline.canon_changes (the outline
    # itself wasn't changed, only the script/shots), but the old commit must
    # have been retired first - exactly one live "fact one" event, not two.
    live_events = await episode_repo.list_canon_events(series.id, before_episode=2)
    assert [e.description for e in live_events] == ["fact one"]
