import json

import pytest

import fixtures as fx
from xerama.config import ModelRoleRegistry, Settings
from xerama.domain.brief import CreativeBrief
from xerama.domain.enums import JobStatus, JudgeDecision, QCStatus
from xerama.pipeline.ai_gateway import AIGateway
from xerama.pipeline.concept_stage import ConceptStage
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


def _full_response_queue(decision: str, title_a: str = "A", title_b: str = "B") -> list[str]:
    return [
        json.dumps(fx.concept(title_a)),
        json.dumps(fx.concept(title_b)),
        json.dumps(fx.judge_result(decision)),
        json.dumps(fx.bible()),
        json.dumps(fx.cast()),
        json.dumps(fx.outline_set(3)),
        json.dumps(fx.script()),
        json.dumps(fx.shot_plan()),
    ]


@pytest.mark.asyncio
async def test_full_pipeline_end_to_end_decision_a(session) -> None:
    provider = FakeLLMProvider(_full_response_queue("A", "Blood Sisters A", "Blood Sisters B"))
    project_repo = SQLAlchemyProjectRepository(session)
    project = await project_repo.create("Trial 01")
    await session.commit()

    showrunner = _showrunner(session, provider)
    brief = CreativeBrief(genre="thriller", episode_count=3, episode_duration_seconds=75)

    result = await showrunner.run(project.id, brief)
    await session.commit()

    assert result.judge_result.decision == JudgeDecision.A
    assert {result.candidate_a.title, result.candidate_b.title} == {"Blood Sisters A", "Blood Sisters B"}
    assert result.approved_concept.title == result.candidate_a.title
    assert result.bible.title == "Blood Sisters"
    assert len(result.cast.characters) == 2
    assert len(result.outlines) == 3
    assert result.episode1_script.scenes[0].dialogue[0].line == "This can't be real."
    assert result.episode1_shot_plan.scenes[0].shots[0].camera.shot_size == "close-up"
    # The fixture shot plan only has one 5s shot against a 75s target, so the
    # runtime-budget heuristic in RetentionValidator correctly warns here.
    assert result.retention_qc.status == QCStatus.WARN
    assert any("deviates" in r for r in result.retention_qc.reasons)
    assert result.continuity_qc.status == QCStatus.PASS

    # Every stage should be independently inspectable afterwards.
    episode_repo = SQLAlchemyEpisodeRepository(session)
    episodes = await episode_repo.list_by_series(result.series_id)
    assert len(episodes) == 3
    fetched_plan = await episode_repo.get_shot_plan(result.episode1_id)
    assert fetched_plan is not None


@pytest.mark.asyncio
async def test_full_pipeline_persists_jobs_for_every_stage(session) -> None:
    provider = FakeLLMProvider(_full_response_queue("B"))
    project_repo = SQLAlchemyProjectRepository(session)
    project = await project_repo.create("Trial 01")
    await session.commit()

    showrunner = _showrunner(session, provider)
    brief = CreativeBrief(genre="thriller", episode_count=3, episode_duration_seconds=75)
    await showrunner.run(project.id, brief)
    await session.commit()

    from sqlalchemy import select

    from xerama.db import models as m

    rows = (await session.execute(select(m.GenerationJob))).scalars().all()
    # concept_generation, judge, concept_merge (still a job even for A/B - no
    # LLM call happens inside it, but the stage transition is still tracked),
    # bible, characters, outlines, script, shots.
    assert len(rows) == 8
    assert all(row.status == JobStatus.SUCCEEDED.value for row in rows)


@pytest.mark.asyncio
async def test_pipeline_stage_failure_leaves_earlier_stages_persisted(session) -> None:
    from xerama.domain.enums import ProviderErrorKind
    from xerama.pipeline.ai_gateway import XeramaGenerationError
    from xerama.providers.errors import ProviderError

    provider = FakeLLMProvider(
        [
            json.dumps(fx.concept("A")),
            json.dumps(fx.concept("B")),
            ProviderError(ProviderErrorKind.AUTHENTICATION, "bad key"),
        ]
    )
    project_repo = SQLAlchemyProjectRepository(session)
    project = await project_repo.create("Trial 01")
    await session.commit()

    showrunner = _showrunner(session, provider)
    brief = CreativeBrief(genre="thriller", episode_count=3, episode_duration_seconds=75)

    with pytest.raises(XeramaGenerationError):
        await showrunner.run(project.id, brief)
    await session.commit()

    from sqlalchemy import select

    from xerama.db import models as m

    candidates = (await session.execute(select(m.ConceptCandidateRecord))).scalars().all()
    jobs = (await session.execute(select(m.GenerationJob))).scalars().all()
    # Both candidates are persisted as soon as concept_generation succeeds,
    # even though the judge stage that follows then fails - see
    # "Every stage must be inspectable" / ADR-019 (never discard candidates).
    assert len(candidates) == 2
    assert len(jobs) == 2
    assert jobs[0].status == JobStatus.SUCCEEDED.value  # concept_generation job
    assert jobs[1].status == JobStatus.FAILED.value  # judge job


@pytest.mark.asyncio
async def test_concept_stage_merge_synthesizes_from_both_candidates(session) -> None:
    merged = fx.concept("Merged Title")
    provider = FakeLLMProvider([json.dumps(merged)])
    gateway = AIGateway(provider=provider, roles=ModelRoleRegistry(Settings()))
    stage = ConceptStage(gateway)

    from xerama.domain.story import ConceptCandidate, JudgeResult

    candidate_a = ConceptCandidate.model_validate(fx.concept("A"))
    candidate_b = ConceptCandidate.model_validate(fx.concept("B"))
    judge = JudgeResult.model_validate(fx.judge_result("MERGE"))

    approved = await stage.resolve_approved_concept(candidate_a, candidate_b, judge)

    assert approved.title == "Merged Title"
    assert len(provider.calls) == 1
