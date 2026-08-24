"""Showrunner - runs the full XER-001 text pipeline end to end.

Idea -> dual concepts -> judge -> approved concept -> series bible ->
characters -> episode outlines -> Episode 1 script -> shots -> retention +
continuity validation -> persisted canon. See README.md "Target Pipeline"
and docs/ARCHITECTURE.md section 14 (Trial 01 scope).

Every stage is wrapped in a persistent `GenerationJob` and its output is
persisted immediately, so a failure partway through still leaves prior
stages inspectable - "Every stage must be inspectable" is an explicit
project requirement.
"""

import uuid
from collections.abc import Awaitable, Coroutine
from typing import TypeVar

from pydantic import BaseModel

from xerama.domain.brief import CreativeBrief
from xerama.domain.canon import CanonSnapshot
from xerama.domain.character import CharacterCast
from xerama.domain.enums import JobStage, ModelRole, QCStatus
from xerama.domain.episode import EpisodeOutline, EpisodeScript
from xerama.domain.quality import QCResult
from xerama.domain.scene import EpisodeShotPlan
from xerama.domain.season import SeasonPlan
from xerama.domain.story import ConceptCandidate, JudgeResult, SeriesBible
from xerama.pipeline.ai_gateway import AIGateway
from xerama.pipeline.bible_stage import BibleStage
from xerama.pipeline.canon_commit import build_canon_events
from xerama.pipeline.character_stage import CharacterStage
from xerama.pipeline.concept_stage import ConceptStage
from xerama.pipeline.episode_stage import EpisodeStage
from xerama.pipeline.season_stage import SeasonStage
from xerama.pipeline.season_validators import SeasonValidator
from xerama.pipeline.shot_stage import ShotStage
from xerama.pipeline.validators import ContinuityValidator, RetentionValidator
from xerama.repositories.interfaces import (
    ConceptRepository,
    EpisodeRepository,
    JobRepository,
    SeasonRepository,
    SeriesRepository,
)

T = TypeVar("T")

# Targeted retry, not whole-episode regeneration - see ADR-019. Bounded to
# one retry for V1; repeated continuity/season-plan failures are left BLOCK
# for human review rather than looping indefinitely.
MAX_SHOT_PLAN_ATTEMPTS = 2
MAX_SEASON_PLAN_ATTEMPTS = 2


class PipelineResult(BaseModel):
    """Every stage artifact from one full pipeline run - the inspectable result."""

    project_id: str
    series_id: str
    batch_id: str
    candidate_a: ConceptCandidate
    candidate_b: ConceptCandidate
    judge_result: JudgeResult
    approved_concept: ConceptCandidate
    bible: SeriesBible
    cast: CharacterCast
    season_plan_id: str
    season_plan: SeasonPlan
    season_qc: QCResult
    outlines: list[EpisodeOutline]
    episode1_id: str
    episode1_script: EpisodeScript
    episode1_shot_plan: EpisodeShotPlan
    retention_qc: QCResult
    continuity_qc: QCResult


class Showrunner:
    def __init__(
        self,
        gateway: AIGateway,
        concept_repo: ConceptRepository,
        series_repo: SeriesRepository,
        season_repo: SeasonRepository,
        episode_repo: EpisodeRepository,
        job_repo: JobRepository,
    ) -> None:
        self._gateway = gateway
        self._concept_repo = concept_repo
        self._series_repo = series_repo
        self._season_repo = season_repo
        self._episode_repo = episode_repo
        self._job_repo = job_repo
        self._concept_stage = ConceptStage(gateway)
        self._bible_stage = BibleStage(gateway)
        self._character_stage = CharacterStage(gateway)
        self._season_stage = SeasonStage(gateway)
        self._episode_stage = EpisodeStage(gateway)
        self._shot_stage = ShotStage(gateway)
        self._season_validator = SeasonValidator()
        self._retention_validator = RetentionValidator()
        self._continuity_validator = ContinuityValidator()

    async def _run_job(
        self,
        project_id: str,
        stage: JobStage,
        model_label: str,
        awaitable: Coroutine[None, None, T] | Awaitable[T],
    ) -> T:
        job = await self._job_repo.create(project_id, stage)
        await self._job_repo.start(job.id, provider="openrouter", model=model_label)
        try:
            result = await awaitable
        except Exception as exc:
            await self._job_repo.fail(job.id, str(exc))
            raise
        await self._job_repo.succeed(job.id)
        return result

    async def run(self, project_id: str, brief: CreativeBrief) -> PipelineResult:
        batch_id = uuid.uuid4().hex
        model_a = self._gateway.resolve_model(ModelRole.CONCEPT_GENERATOR_A)
        model_b = self._gateway.resolve_model(ModelRole.CONCEPT_GENERATOR_B)

        candidate_a, candidate_b = await self._run_job(
            project_id,
            JobStage.CONCEPT_GENERATION,
            f"{model_a}|{model_b}",
            self._concept_stage.generate_candidates(brief),
        )
        await self._concept_repo.save_candidate(
            project_id, batch_id, "A", "openrouter", model_a, brief, candidate_a
        )
        await self._concept_repo.save_candidate(
            project_id, batch_id, "B", "openrouter", model_b, brief, candidate_b
        )

        judge_result = await self._run_job(
            project_id,
            JobStage.JUDGE,
            self._gateway.resolve_model(ModelRole.JUDGE),
            self._concept_stage.judge(brief, candidate_a, candidate_b),
        )

        approved_concept = await self._run_job(
            project_id,
            JobStage.CONCEPT_MERGE,
            self._gateway.resolve_model(ModelRole.STORY_ARCHITECT),
            self._concept_stage.resolve_approved_concept(candidate_a, candidate_b, judge_result),
        )
        await self._concept_repo.save_judge_decision(
            project_id,
            batch_id,
            "openrouter",
            self._gateway.resolve_model(ModelRole.JUDGE),
            judge_result,
            approved_concept,
        )

        series = await self._series_repo.create_series(project_id, brief, approved_concept)

        bible = await self._run_job(
            project_id,
            JobStage.SERIES_BIBLE,
            self._gateway.resolve_model(ModelRole.STORY_ARCHITECT),
            self._bible_stage.generate_series_bible(brief, approved_concept),
        )
        await self._series_repo.save_bible(series.id, bible)

        cast = await self._run_job(
            project_id,
            JobStage.CHARACTERS,
            self._gateway.resolve_model(ModelRole.STORY_ARCHITECT),
            self._character_stage.generate_cast(bible),
        )
        await self._series_repo.save_cast(series.id, cast)

        season_plan_model = self._gateway.resolve_model(ModelRole.STORY_ARCHITECT)
        season_feedback = ""
        for attempt in range(1, MAX_SEASON_PLAN_ATTEMPTS + 1):
            season_plan = await self._run_job(
                project_id,
                JobStage.SEASON_PLAN,
                season_plan_model,
                self._season_stage.generate_season_plan(
                    bible, cast, brief.episode_count, feedback=season_feedback
                ),
            )
            season_qc = self._season_validator.validate(season_plan, cast)
            # Every attempt is persisted as a new version - never overwritten
            # - so a rejected season plan stays inspectable (ADR-019).
            season_plan_record = await self._season_repo.create_plan(series.id, season_plan, season_qc)
            if season_qc.status != QCStatus.BLOCK or attempt == MAX_SEASON_PLAN_ATTEMPTS:
                break
            season_feedback = "; ".join(season_qc.reasons)

        outlines = await self._run_job(
            project_id,
            JobStage.EPISODE_OUTLINES,
            self._gateway.resolve_model(ModelRole.STORY_ARCHITECT),
            self._episode_stage.generate_outlines(bible, cast, brief.episode_count, season_plan=season_plan),
        )
        episode_ids_by_number: dict[int, str] = {}
        for outline in outlines:
            record = await self._episode_repo.save_outline(series.id, outline)
            episode_ids_by_number[outline.episode_number] = record.id

        episode1_outline = next(o for o in outlines if o.episode_number == 1)
        episode1_id = episode_ids_by_number[1]

        canon = CanonSnapshot(series_title=bible.title, locked_facts=bible.locked_facts)
        episode1_script = await self._run_job(
            project_id,
            JobStage.EPISODE_SCRIPT,
            self._gateway.resolve_model(ModelRole.EPISODE_WRITER),
            self._episode_stage.generate_script(bible, cast, episode1_outline, canon),
        )
        await self._episode_repo.save_script(episode1_id, episode1_script)

        shot_planner_model = self._gateway.resolve_model(ModelRole.SHOT_PLANNER)
        feedback = ""
        for attempt in range(1, MAX_SHOT_PLAN_ATTEMPTS + 1):
            episode1_shot_plan = await self._run_job(
                project_id,
                JobStage.SCENE_SHOT_PLANNING,
                shot_planner_model,
                self._shot_stage.plan_shots(episode1_script, feedback=feedback),
            )
            await self._episode_repo.save_shot_plan(episode1_id, episode1_shot_plan)

            retention_qc = self._retention_validator.validate(
                episode1_outline, episode1_script, episode1_shot_plan
            )
            continuity_qc = self._continuity_validator.validate(
                cast, episode1_script, episode1_shot_plan
            )
            # Both reports are saved on every attempt (never overwritten) so
            # a rejected take's reasons stay available for benchmarking -
            # see ADR-019.
            await self._episode_repo.save_quality_report(episode1_id, retention_qc)
            await self._episode_repo.save_quality_report(episode1_id, continuity_qc)

            if continuity_qc.status != QCStatus.BLOCK or attempt == MAX_SHOT_PLAN_ATTEMPTS:
                break
            feedback = "; ".join(continuity_qc.reasons)

        if retention_qc.status != QCStatus.BLOCK and continuity_qc.status != QCStatus.BLOCK:
            for event in build_canon_events(episode1_outline.episode_number, episode1_outline.canon_changes):
                await self._episode_repo.save_canon_event(episode1_id, event)

        return PipelineResult(
            project_id=project_id,
            series_id=series.id,
            batch_id=batch_id,
            candidate_a=candidate_a,
            candidate_b=candidate_b,
            judge_result=judge_result,
            approved_concept=approved_concept,
            bible=bible,
            cast=cast,
            season_plan_id=season_plan_record.id,
            season_plan=season_plan,
            season_qc=season_qc,
            outlines=outlines,
            episode1_id=episode1_id,
            episode1_script=episode1_script,
            episode1_shot_plan=episode1_shot_plan,
            retention_qc=retention_qc,
            continuity_qc=continuity_qc,
        )
