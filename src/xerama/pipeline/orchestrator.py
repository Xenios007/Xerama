"""Showrunner - runs the full XER-001+ text pipeline end to end.

Idea -> dual concepts -> judge -> approved concept -> series bible ->
characters -> season plan -> episode outlines -> Episode 1 (script/shots/QC/
canon commit via `EpisodeEngine`). See README.md "Target Pipeline" and
docs/ARCHITECTURE.md section 14 (Trial 01 scope).

Episodes 2..N already have outlines after this run but are not scripted
automatically - see modules/02_MULTI_EPISODE_ENGINE.md: use
`EpisodeEngine.generate_episode/generate_next_unfinished/generate_range`
(exposed via `POST /series/{id}/episodes/...`) to continue the season one
episode, a range, or "the next unfinished episode" at a time.

Every stage is wrapped in a persistent `GenerationJob` and its output is
persisted immediately, so a failure partway through still leaves prior
stages inspectable - "Every stage must be inspectable" is an explicit
project requirement.
"""

import uuid

from pydantic import BaseModel

from xerama.domain.brief import CreativeBrief
from xerama.domain.character import CharacterCast
from xerama.domain.enums import JobStage, ModelRole, QCStatus
from xerama.domain.episode import EpisodeOutline, EpisodeScript
from xerama.domain.quality import QCResult
from xerama.domain.scene import EpisodeShotPlan
from xerama.domain.season import SeasonPlan
from xerama.domain.story import ConceptCandidate, JudgeResult, SeriesBible
from xerama.pipeline.ai_gateway import AIGateway
from xerama.pipeline.bible_stage import BibleStage
from xerama.pipeline.character_stage import CharacterStage
from xerama.pipeline.concept_stage import ConceptStage
from xerama.pipeline.episode_engine import EpisodeEngine
from xerama.pipeline.episode_stage import EpisodeStage
from xerama.pipeline.job_runner import JobRunner
from xerama.pipeline.season_stage import SeasonStage
from xerama.pipeline.season_validators import SeasonValidator
from xerama.repositories.interfaces import (
    ConceptRepository,
    EpisodeRepository,
    JobRepository,
    SeasonRepository,
    SeriesRepository,
)

# Targeted retry, not whole-episode regeneration - see ADR-019. Bounded to
# one retry for V1; repeated season-plan failures are left BLOCK for human
# review rather than looping indefinitely.
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
        self._jobs = JobRunner(job_repo)
        self._concept_stage = ConceptStage(gateway)
        self._bible_stage = BibleStage(gateway)
        self._character_stage = CharacterStage(gateway)
        self._season_stage = SeasonStage(gateway)
        self._episode_stage = EpisodeStage(gateway)
        self._season_validator = SeasonValidator()
        self._episode_engine = EpisodeEngine(gateway, series_repo, episode_repo, job_repo)

    async def run(self, project_id: str, brief: CreativeBrief) -> PipelineResult:
        batch_id = uuid.uuid4().hex
        model_a = self._gateway.resolve_model(ModelRole.CONCEPT_GENERATOR_A)
        model_b = self._gateway.resolve_model(ModelRole.CONCEPT_GENERATOR_B)

        candidate_a, candidate_b = await self._jobs.run(
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

        judge_result = await self._jobs.run(
            project_id,
            JobStage.JUDGE,
            self._gateway.resolve_model(ModelRole.JUDGE),
            self._concept_stage.judge(brief, candidate_a, candidate_b),
        )

        approved_concept = await self._jobs.run(
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

        bible = await self._jobs.run(
            project_id,
            JobStage.SERIES_BIBLE,
            self._gateway.resolve_model(ModelRole.STORY_ARCHITECT),
            self._bible_stage.generate_series_bible(brief, approved_concept),
        )
        await self._series_repo.save_bible(series.id, bible)

        cast = await self._jobs.run(
            project_id,
            JobStage.CHARACTERS,
            self._gateway.resolve_model(ModelRole.STORY_ARCHITECT),
            self._character_stage.generate_cast(bible),
        )
        await self._series_repo.save_cast(series.id, cast)

        season_plan_model = self._gateway.resolve_model(ModelRole.STORY_ARCHITECT)
        season_feedback = ""
        for attempt in range(1, MAX_SEASON_PLAN_ATTEMPTS + 1):
            season_plan = await self._jobs.run(
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

        outlines = await self._jobs.run(
            project_id,
            JobStage.EPISODE_OUTLINES,
            self._gateway.resolve_model(ModelRole.STORY_ARCHITECT),
            self._episode_stage.generate_outlines(bible, cast, brief.episode_count, season_plan=season_plan),
        )
        for outline in outlines:
            await self._episode_repo.save_outline(series.id, outline)

        episode1 = await self._episode_engine.generate_episode(project_id, series.id, 1)

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
            episode1_id=episode1.episode_id,
            episode1_script=episode1.script,
            episode1_shot_plan=episode1.shot_plan,
            retention_qc=episode1.retention_qc,
            continuity_qc=episode1.continuity_qc,
        )
