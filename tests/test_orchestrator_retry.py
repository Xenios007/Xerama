import json

import pytest

import fixtures as fx
from xerama.config import ModelRoleRegistry, Settings
from xerama.domain.brief import CreativeBrief
from xerama.domain.enums import CanonChangeType, QCStatus
from xerama.pipeline.ai_gateway import AIGateway
from xerama.pipeline.orchestrator import Showrunner
from xerama.providers.fake import FakeLLMProvider
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyConceptRepository,
    SQLAlchemyEpisodeRepository,
    SQLAlchemyJobRepository,
    SQLAlchemyProjectRepository,
    SQLAlchemySeriesRepository,
)


def _showrunner(session, provider: FakeLLMProvider) -> Showrunner:
    gateway = AIGateway(provider=provider, roles=ModelRoleRegistry(Settings()))
    return Showrunner(
        gateway=gateway,
        concept_repo=SQLAlchemyConceptRepository(session),
        series_repo=SQLAlchemySeriesRepository(session),
        episode_repo=SQLAlchemyEpisodeRepository(session),
        job_repo=SQLAlchemyJobRepository(session),
    )


def _broken_shot_plan() -> dict:
    plan = fx.shot_plan()
    # Reference a character that doesn't exist in the cast - triggers a
    # continuity BLOCK on the first attempt.
    plan["scenes"][0]["shots"][0]["character_ids"] = ["CHAR_999"]
    return plan


@pytest.mark.asyncio
async def test_continuity_block_triggers_one_targeted_retry(session) -> None:
    provider = FakeLLMProvider(
        [
            json.dumps(fx.concept("A")),
            json.dumps(fx.concept("B")),
            json.dumps(fx.judge_result("A")),
            json.dumps(fx.bible()),
            json.dumps(fx.cast()),
            json.dumps(fx.outline_set(3)),
            json.dumps(fx.script()),
            json.dumps(_broken_shot_plan()),  # attempt 1: BLOCKed
            json.dumps(fx.shot_plan()),  # attempt 2: corrected, passes
        ]
    )
    project_repo = SQLAlchemyProjectRepository(session)
    project = await project_repo.create("Trial 01")
    await session.commit()

    showrunner = _showrunner(session, provider)
    brief = CreativeBrief(genre="thriller", episode_count=3, episode_duration_seconds=75)
    result = await showrunner.run(project.id, brief)
    await session.commit()

    # Final result reflects the corrected (second) shot plan.
    assert result.episode1_shot_plan.scenes[0].shots[0].character_ids == ["CHAR_001"]
    assert result.continuity_qc.status == QCStatus.PASS

    # The retry feedback should have been threaded into the second call.
    second_shot_call = provider.calls[-1]
    assert "rejected by continuity QC" in second_shot_call.messages[-1].content
    assert "CHAR_999" in second_shot_call.messages[-1].content

    from sqlalchemy import select

    from xerama.db import models as m

    jobs = (await session.execute(select(m.GenerationJob))).scalars().all()
    shot_jobs = [j for j in jobs if j.stage == "scene_shot_planning"]
    assert len(shot_jobs) == 2
    assert all(j.status == "succeeded" for j in shot_jobs)

    qc_rows = (await session.execute(select(m.QualityReport))).scalars().all()
    continuity_rows = [r for r in qc_rows if r.gate == "continuity"]
    assert len(continuity_rows) == 2
    assert continuity_rows[0].status == "block"
    assert continuity_rows[1].status == "pass"


@pytest.mark.asyncio
async def test_persistent_continuity_block_gives_up_after_max_attempts(session) -> None:
    provider = FakeLLMProvider(
        [
            json.dumps(fx.concept("A")),
            json.dumps(fx.concept("B")),
            json.dumps(fx.judge_result("A")),
            json.dumps(fx.bible()),
            json.dumps(fx.cast()),
            json.dumps(fx.outline_set(3)),
            json.dumps(fx.script()),
            json.dumps(_broken_shot_plan()),  # attempt 1: BLOCKed
            json.dumps(_broken_shot_plan()),  # attempt 2: still BLOCKed - gives up
        ]
    )
    project_repo = SQLAlchemyProjectRepository(session)
    project = await project_repo.create("Trial 01")
    await session.commit()

    showrunner = _showrunner(session, provider)
    brief = CreativeBrief(genre="thriller", episode_count=3, episode_duration_seconds=75)
    result = await showrunner.run(project.id, brief)
    await session.commit()

    assert result.continuity_qc.status == QCStatus.BLOCK
    assert len(provider.calls) == 9  # no third attempt


@pytest.mark.asyncio
async def test_canon_changes_committed_when_qc_not_blocked(session) -> None:
    outline_set = fx.outline_set(3)
    outline_set["outlines"][0]["canon_changes"] = ["Mara steals the ring", "Lena's secret is exposed"]

    provider = FakeLLMProvider(
        [
            json.dumps(fx.concept("A")),
            json.dumps(fx.concept("B")),
            json.dumps(fx.judge_result("A")),
            json.dumps(fx.bible()),
            json.dumps(fx.cast()),
            json.dumps(outline_set),
            json.dumps(fx.script()),
            json.dumps(fx.shot_plan()),
        ]
    )
    project_repo = SQLAlchemyProjectRepository(session)
    project = await project_repo.create("Trial 01")
    await session.commit()

    showrunner = _showrunner(session, provider)
    brief = CreativeBrief(genre="thriller", episode_count=3, episode_duration_seconds=75)
    result = await showrunner.run(project.id, brief)
    await session.commit()

    assert result.continuity_qc.status != QCStatus.BLOCK

    from sqlalchemy import select

    from xerama.db import models as m

    events = (
        await session.execute(
            select(m.EpisodeStateChange).where(m.EpisodeStateChange.episode_id == result.episode1_id)
        )
    ).scalars().all()
    assert len(events) == 2
    change_types = {e.change_type for e in events}
    assert change_types == {
        CanonChangeType.PROP_OWNERSHIP_CHANGE.value,
        CanonChangeType.SECRET_EXPOSED.value,
    }
    assert all(e.committed for e in events)


@pytest.mark.asyncio
async def test_canon_changes_not_committed_when_continuity_blocked(session) -> None:
    outline_set = fx.outline_set(3)
    outline_set["outlines"][0]["canon_changes"] = ["Mara steals the ring"]

    provider = FakeLLMProvider(
        [
            json.dumps(fx.concept("A")),
            json.dumps(fx.concept("B")),
            json.dumps(fx.judge_result("A")),
            json.dumps(fx.bible()),
            json.dumps(fx.cast()),
            json.dumps(outline_set),
            json.dumps(fx.script()),
            json.dumps(_broken_shot_plan()),
            json.dumps(_broken_shot_plan()),
        ]
    )
    project_repo = SQLAlchemyProjectRepository(session)
    project = await project_repo.create("Trial 01")
    await session.commit()

    showrunner = _showrunner(session, provider)
    brief = CreativeBrief(genre="thriller", episode_count=3, episode_duration_seconds=75)
    result = await showrunner.run(project.id, brief)
    await session.commit()

    assert result.continuity_qc.status == QCStatus.BLOCK

    from sqlalchemy import select

    from xerama.db import models as m

    events = (
        await session.execute(
            select(m.EpisodeStateChange).where(m.EpisodeStateChange.episode_id == result.episode1_id)
        )
    ).scalars().all()
    assert events == []
