import pytest

from xerama.domain.brief import CreativeBrief
from xerama.domain.character import Character, CharacterCast, CharacterDNA, RelationshipState
from xerama.domain.enums import CanonChangeType, CliffhangerType, JobStage, JudgeDecision, QCStatus, ScreenPosition
from xerama.domain.canon import CanonEvent
from xerama.domain.episode import Cliffhanger, DialogueLine, EpisodeOutline, EpisodeScript, ScriptScene
from xerama.domain.quality import QCResult
from xerama.domain.scene import Camera, CharacterBlock, EpisodeShotPlan, Scene, SceneBlocking, Shot, Visual
from xerama.domain.story import CandidateScore, JudgeCriteria, JudgeResult, Protagonist, ConceptCandidate
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyConceptRepository,
    SQLAlchemyEpisodeRepository,
    SQLAlchemyJobRepository,
    SQLAlchemyProjectRepository,
    SQLAlchemySeriesRepository,
)

def _brief() -> CreativeBrief:
    return CreativeBrief(genre="thriller", episode_count=3, episode_duration_seconds=75)


def _candidate(title: str) -> ConceptCandidate:
    return ConceptCandidate(
        title=title,
        genre=["thriller"],
        logline="A woman uncovers her sister's secret double life.",
        premise="premise",
        protagonist=Protagonist(name="Mara", role="protagonist", desire="the truth", flaw="pride"),
        antagonistic_force="her own family",
        central_conflict="loyalty vs. justice",
        central_secret="the sister faked her death",
        emotional_engine="betrayal",
        opening_hook="a funeral, and a text message from the dead",
        serial_engine="who else is lying",
        ending_direction="reconciliation or ruin",
    )


async def test_project_repository_roundtrip(session) -> None:
    repo = SQLAlchemyProjectRepository(session)
    created = await repo.create("Trial 01", "first pilot")
    await session.commit()

    fetched = await repo.get(created.id)
    assert fetched is not None
    assert fetched.name == "Trial 01"
    assert await repo.get("does-not-exist") is None


async def test_concept_repository_marks_accepted_candidate(session) -> None:
    project_repo = SQLAlchemyProjectRepository(session)
    concept_repo = SQLAlchemyConceptRepository(session)
    project = await project_repo.create("p")
    brief = _brief()
    candidate_a = _candidate("A title")
    candidate_b = _candidate("B title")

    batch_id = "batch-1"
    await concept_repo.save_candidate(project.id, batch_id, "A", "openrouter", "model-a", brief, candidate_a)
    await concept_repo.save_candidate(project.id, batch_id, "B", "openrouter", "model-b", brief, candidate_b)

    judge_result = JudgeResult(
        decision=JudgeDecision.B,
        candidate_a=CandidateScore(score=6, strengths=[]),
        candidate_b=CandidateScore(score=8, strengths=["stronger hook"]),
        criteria=JudgeCriteria(
            hook=8,
            emotional_intensity=7,
            conflict=7,
            originality=6,
            serial_potential=8,
            reversal_potential=7,
            cliffhanger_potential=9,
            production_feasibility=8,
            character_potential=7,
        ),
        reason="B wins on hook and cliffhanger potential.",
    )
    await concept_repo.save_judge_decision(project.id, batch_id, "openrouter", "judge-model", judge_result, candidate_b)
    await session.commit()

    from sqlalchemy import select
    from xerama.db import models as m

    rows = (
        await session.execute(
            select(m.ConceptCandidateRecord).where(m.ConceptCandidateRecord.batch_id == batch_id)
        )
    ).scalars().all()
    accepted = {row.slot: row.accepted for row in rows}
    assert accepted == {"A": False, "B": True}


async def test_series_bible_and_cast_roundtrip(session) -> None:
    project_repo = SQLAlchemyProjectRepository(session)
    series_repo = SQLAlchemySeriesRepository(session)
    project = await project_repo.create("p")
    brief = _brief()
    approved = _candidate("Approved")

    series = await series_repo.create_series(project.id, brief, approved)
    assert series.title == "Approved"

    from xerama.domain.story import SeriesBible

    bible = SeriesBible(
        title="Approved",
        logline="logline",
        genres=["thriller"],
        target_audience="general",
        episode_count=3,
        episode_duration_seconds=75,
        premise="premise",
        emotional_engine="betrayal",
        central_dramatic_question="who is lying?",
        central_secret="the sister faked her death",
        ending_target="reconciliation",
        locked_facts=["Mara has a twin sister"],
    )
    await series_repo.save_bible(series.id, bible)
    await session.commit()

    fetched_bible = await series_repo.get_bible(series.id)
    assert fetched_bible is not None
    assert fetched_bible.locked_facts == ["Mara has a twin sister"]
    assert fetched_bible.title == "Approved"

    cast = CharacterCast(
        characters=[
            Character(
                id="CHAR_001",
                name="Mara",
                role="protagonist",
                goal="find her sister",
                fear="being alone",
                flaw="pride",
                secret="she knew all along",
                character_dna=CharacterDNA(eyes="brown"),
            ),
            Character(id="CHAR_002", name="Lena", role="antagonist"),
        ],
        relationships=[
            RelationshipState(
                source_character_id="CHAR_001",
                target_character_id="CHAR_002",
                relationship_type="sisters",
            )
        ],
    )
    await series_repo.save_cast(series.id, cast)
    await session.commit()

    fetched_cast = await series_repo.get_cast(series.id)
    assert {c.id for c in fetched_cast.characters} == {"CHAR_001", "CHAR_002"}
    assert fetched_cast.relationships[0].relationship_type == "sisters"


async def test_episode_outline_script_shots_and_qc_roundtrip(session) -> None:
    project_repo = SQLAlchemyProjectRepository(session)
    series_repo = SQLAlchemySeriesRepository(session)
    episode_repo = SQLAlchemyEpisodeRepository(session)

    project = await project_repo.create("p")
    series = await series_repo.create_series(project.id, _brief(), _candidate("T"))
    await session.commit()

    outline = EpisodeOutline(
        episode_number=1,
        objective="find the truth",
        opening_hook="a scream in the dark",
        stakes="her freedom",
        conflict="sister vs. sister",
        turn="the letter was a forgery",
        reveal="he was never who he claimed",
        duration_target_seconds=75,
        cliffhanger=Cliffhanger(type=CliffhangerType.IDENTITY_REVEAL, event="the mask comes off"),
    )
    record = await episode_repo.save_outline(series.id, outline)
    await session.commit()
    assert record.episode_number == 1
    assert record.script is None

    script = EpisodeScript(
        episode_number=1,
        title="Episode 1",
        scenes=[
            ScriptScene(
                scene_number=1,
                location="apartment",
                characters=["CHAR_001"],
                action="Mara reads the letter.",
                dialogue=[DialogueLine(character_id="CHAR_001", character_name="Mara", line="This can't be real.")],
            )
        ],
        estimated_duration_seconds=75,
    )
    await episode_repo.save_script(record.id, script)
    await session.commit()

    fetched = await episode_repo.get(record.id)
    assert fetched is not None
    assert fetched.script is not None
    assert fetched.script.scenes[0].dialogue[0].line == "This can't be real."

    plan = EpisodeShotPlan(
        episode_number=1,
        scenes=[
            Scene(
                scene_number=1,
                location="apartment",
                characters=["CHAR_001"],
                shots=[
                    Shot(
                        shot_number=1,
                        scene_number=1,
                        character_ids=["CHAR_001"],
                        action="Mara opens the letter",
                        duration_seconds=4,
                        camera=Camera(shot_size="close-up"),
                        visual=Visual(emotion="dread"),
                        blocking_plan=SceneBlocking(
                            characters=[CharacterBlock(character_id="CHAR_001", position=ScreenPosition.LEFT)],
                            screen_direction="left_to_right",
                        ),
                    )
                ],
            )
        ],
    )
    await episode_repo.save_shot_plan(record.id, plan)
    await session.commit()

    fetched_plan = await episode_repo.get_shot_plan(record.id)
    assert fetched_plan is not None
    assert fetched_plan.scenes[0].shots[0].camera.shot_size == "close-up"
    assert fetched_plan.scenes[0].shots[0].blocking_plan.screen_direction == "left_to_right"
    assert fetched_plan.scenes[0].shots[0].blocking_plan.characters[0].position == ScreenPosition.LEFT

    await episode_repo.save_quality_report(
        record.id, QCResult(gate="retention", status=QCStatus.PASS, score=9.0)
    )
    await episode_repo.save_canon_event(
        record.id,
        CanonEvent(
            change_type=CanonChangeType.SECRET_EXPOSED,
            episode_number=1,
            description="Mara learns Lena is alive",
            committed=True,
        ),
    )
    await session.commit()

    episodes = await episode_repo.list_by_series(series.id)
    assert len(episodes) == 1


async def test_job_repository_state_transitions(session) -> None:
    project_repo = SQLAlchemyProjectRepository(session)
    job_repo = SQLAlchemyJobRepository(session)
    project = await project_repo.create("p")
    await session.commit()

    job = await job_repo.create(project.id, JobStage.CONCEPT_GENERATION)
    from xerama.domain.enums import JobStatus

    assert job.status == JobStatus.QUEUED

    await job_repo.start(job.id, provider="openrouter", model="model-a")
    fetched = await job_repo.get(job.id)
    assert fetched.status == JobStatus.RUNNING
    assert fetched.model == "model-a"

    await job_repo.succeed(job.id)
    fetched = await job_repo.get(job.id)
    assert fetched.status == JobStatus.SUCCEEDED


async def test_job_repository_failure(session) -> None:
    project_repo = SQLAlchemyProjectRepository(session)
    job_repo = SQLAlchemyJobRepository(session)
    project = await project_repo.create("p")
    await session.commit()

    job = await job_repo.create(project.id, JobStage.JUDGE)
    await job_repo.start(job.id)
    await job_repo.fail(job.id, "provider timed out")

    fetched = await job_repo.get(job.id)
    from xerama.domain.enums import JobStatus

    assert fetched.status == JobStatus.FAILED
    assert fetched.error == "provider timed out"
