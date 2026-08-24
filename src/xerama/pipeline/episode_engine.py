"""Multi-Episode Engine (Module 02).

Generates, validates and canon-commits Episode 1..N individually, given the
season plan + outlines already produced by `Showrunner`/`SeasonStage`.
Workflow per episode: outline (already approved) -> script -> scenes/shots
-> story QC -> canon commit. Canon for episode N+1 is built only from
episodes < N that reached `CANON_COMMITTED` - never from raw prior scripts
(see `pipeline/canon_builder.py`) and never from an episode whose QC
BLOCKed (see docs/DATA_MODEL.md "Canon Commit Rule" / ADR-006).

Regenerating an already-committed episode retires (not deletes) its old
canon events and marks every downstream committed episode `STALE` rather
than silently leaving them built on canon that no longer holds - see
ADR-019 and research/WIND_COMIC_DEEP_DIVE.md section 24 (dirty propagation,
"Trial 01 can begin with coarse stage invalidation").
"""

from pydantic import BaseModel

from xerama.domain.enums import EpisodeGenerationStatus, JobStage, ModelRole, QCStatus
from xerama.domain.episode import EpisodeScript
from xerama.domain.quality import QCResult
from xerama.domain.scene import EpisodeShotPlan
from xerama.pipeline.ai_gateway import AIGateway
from xerama.pipeline.canon_builder import build_canon_snapshot
from xerama.pipeline.canon_commit import build_canon_events
from xerama.pipeline.episode_stage import EpisodeStage
from xerama.pipeline.job_runner import JobRunner
from xerama.pipeline.shot_stage import ShotStage
from xerama.pipeline.validators import ContinuityValidator, RetentionValidator
from xerama.repositories.interfaces import EpisodeRepository, JobRepository, SeriesRepository

# Targeted retry, not whole-episode regeneration - see ADR-019.
MAX_SHOT_PLAN_ATTEMPTS = 2


class EpisodeGenerationResult(BaseModel):
    episode_id: str
    episode_number: int
    version: int
    script: EpisodeScript
    shot_plan: EpisodeShotPlan
    retention_qc: QCResult
    continuity_qc: QCResult
    canon_committed: bool


class EpisodeEngine:
    def __init__(
        self,
        gateway: AIGateway,
        series_repo: SeriesRepository,
        episode_repo: EpisodeRepository,
        job_repo: JobRepository,
    ) -> None:
        self._gateway = gateway
        self._series_repo = series_repo
        self._episode_repo = episode_repo
        self._jobs = JobRunner(job_repo)
        self._episode_stage = EpisodeStage(gateway)
        self._shot_stage = ShotStage(gateway)
        self._retention_validator = RetentionValidator()
        self._continuity_validator = ContinuityValidator()

    async def generate_episode(
        self, project_id: str, series_id: str, episode_number: int
    ) -> EpisodeGenerationResult:
        bible = await self._series_repo.get_bible(series_id)
        if bible is None:
            raise ValueError(f"series {series_id} has no approved Series Bible yet")
        cast = await self._series_repo.get_cast(series_id)

        episode_record = await self._episode_repo.get_by_number(series_id, episode_number)
        if episode_record is None:
            raise ValueError(
                f"episode {episode_number} has no outline yet - generate season/outlines first"
            )
        outline = episode_record.outline
        is_regeneration = episode_record.status in (
            EpisodeGenerationStatus.CANON_COMMITTED.value,
            EpisodeGenerationStatus.QC_BLOCKED.value,
            EpisodeGenerationStatus.STALE.value,
        )

        all_episodes = await self._episode_repo.list_by_series(series_id)
        prior_committed = [
            e
            for e in all_episodes
            if e.episode_number < episode_number
            and e.status == EpisodeGenerationStatus.CANON_COMMITTED.value
        ]
        committed_events = await self._episode_repo.list_canon_events(
            series_id, before_episode=episode_number
        )
        canon = build_canon_snapshot(bible, cast, prior_committed, committed_events)

        script = await self._jobs.run(
            project_id,
            JobStage.EPISODE_SCRIPT,
            self._gateway.resolve_model(ModelRole.EPISODE_WRITER),
            self._episode_stage.generate_script(bible, cast, outline, canon),
        )
        await self._episode_repo.save_script(episode_record.id, script)

        shot_planner_model = self._gateway.resolve_model(ModelRole.SHOT_PLANNER)
        feedback = ""
        for attempt in range(1, MAX_SHOT_PLAN_ATTEMPTS + 1):
            shot_plan = await self._jobs.run(
                project_id,
                JobStage.SCENE_SHOT_PLANNING,
                shot_planner_model,
                self._shot_stage.plan_shots(script, feedback=feedback),
            )
            await self._episode_repo.save_shot_plan(episode_record.id, shot_plan)

            recent_cliffhangers = [e.outline.cliffhanger.type for e in prior_committed]
            retention_qc = self._retention_validator.validate(
                outline, script, shot_plan, recent_cliffhanger_types=recent_cliffhangers
            )
            continuity_qc = self._continuity_validator.validate(cast, script, shot_plan)
            await self._episode_repo.save_quality_report(episode_record.id, retention_qc)
            await self._episode_repo.save_quality_report(episode_record.id, continuity_qc)

            if continuity_qc.status != QCStatus.BLOCK or attempt == MAX_SHOT_PLAN_ATTEMPTS:
                break
            feedback = "; ".join(continuity_qc.reasons)

        canon_committed = False
        if retention_qc.status != QCStatus.BLOCK and continuity_qc.status != QCStatus.BLOCK:
            if is_regeneration:
                # Retire this episode's previous canon commit before
                # recording the new one - never leave both "live" at once.
                await self._episode_repo.invalidate_canon_events(episode_record.id)
            for event in build_canon_events(episode_number, outline.canon_changes):
                await self._episode_repo.save_canon_event(episode_record.id, event)
            await self._episode_repo.set_status(
                episode_record.id, EpisodeGenerationStatus.CANON_COMMITTED.value
            )
            canon_committed = True
            await self._invalidate_downstream(series_id, episode_number)
        else:
            await self._episode_repo.set_status(
                episode_record.id, EpisodeGenerationStatus.QC_BLOCKED.value
            )

        updated_record = await self._episode_repo.get(episode_record.id)
        version = updated_record.version if updated_record else episode_record.version

        return EpisodeGenerationResult(
            episode_id=episode_record.id,
            episode_number=episode_number,
            version=version,
            script=script,
            shot_plan=shot_plan,
            retention_qc=retention_qc,
            continuity_qc=continuity_qc,
            canon_committed=canon_committed,
        )

    async def _invalidate_downstream(self, series_id: str, episode_number: int) -> None:
        for episode in await self._episode_repo.list_by_series(series_id):
            if (
                episode.episode_number > episode_number
                and episode.status == EpisodeGenerationStatus.CANON_COMMITTED.value
            ):
                await self._episode_repo.set_status(
                    episode.id, EpisodeGenerationStatus.STALE.value
                )

    async def generate_next_unfinished(
        self, project_id: str, series_id: str
    ) -> EpisodeGenerationResult:
        episodes = await self._episode_repo.list_by_series(series_id)
        if not episodes:
            raise ValueError(f"series {series_id} has no episode outlines yet")
        unfinished = sorted(
            (
                e.episode_number
                for e in episodes
                if e.status != EpisodeGenerationStatus.CANON_COMMITTED.value
            )
        )
        if not unfinished:
            raise ValueError(f"series {series_id} has no unfinished episodes")
        return await self.generate_episode(project_id, series_id, unfinished[0])

    async def generate_range(
        self, project_id: str, series_id: str, start: int, end: int
    ) -> list[EpisodeGenerationResult]:
        if start > end:
            raise ValueError("start must be <= end")
        results = []
        # Sequential, not concurrent: episode N+1's canon depends on N
        # actually being committed first.
        for episode_number in range(start, end + 1):
            results.append(await self.generate_episode(project_id, series_id, episode_number))
        return results
