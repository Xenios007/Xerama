"""SQLAlchemy-backed implementations of the repository Protocols in
`interfaces.py`. Pipeline/service code should type-hint against the
Protocols, not import this module directly, so a future backend swap stays
localized (ADR-021)."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from xerama.db import models as m
from xerama.db.base import utcnow
from xerama.domain.brief import CreativeBrief
from xerama.domain.canon import CanonEvent
from xerama.domain.character import Character, CharacterCast, RelationshipState
from xerama.domain.enums import JobStage, JobStatus
from xerama.domain.episode import EpisodeOutline, EpisodeScript
from xerama.domain.quality import QCResult
from xerama.domain.scene import EpisodeShotPlan, Scene as SceneDTO, Shot as ShotDTO
from xerama.domain.season import SeasonPlan
from xerama.domain.story import ConceptCandidate, JudgeResult, SeriesBible
from xerama.repositories.interfaces import (
    EpisodeRecord,
    JobRecord,
    ProjectRecord,
    SeasonPlanRecord,
    SeriesRecord,
)


class SQLAlchemyProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, name: str, description: str = "") -> ProjectRecord:
        row = m.Project(name=name, description=description)
        self._session.add(row)
        await self._session.flush()
        return ProjectRecord(id=row.id, name=row.name, description=row.description, status=row.status, created_at=row.created_at)

    async def get(self, project_id: str) -> ProjectRecord | None:
        row = await self._session.get(m.Project, project_id)
        if row is None:
            return None
        return ProjectRecord(id=row.id, name=row.name, description=row.description, status=row.status, created_at=row.created_at)


class SQLAlchemyConceptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_candidate(
        self,
        project_id: str,
        batch_id: str,
        slot: str,
        provider: str,
        model: str,
        brief: CreativeBrief,
        candidate: ConceptCandidate,
    ) -> str:
        row = m.ConceptCandidateRecord(
            project_id=project_id,
            batch_id=batch_id,
            slot=slot,
            provider=provider,
            model=model,
            brief=brief.model_dump(mode="json"),
            candidate=candidate.model_dump(mode="json"),
        )
        self._session.add(row)
        await self._session.flush()
        return row.id

    async def save_judge_decision(
        self,
        project_id: str,
        batch_id: str,
        provider: str,
        model: str,
        result: JudgeResult,
        approved_concept: ConceptCandidate,
    ) -> str:
        row = m.JudgeDecisionRecord(
            project_id=project_id,
            batch_id=batch_id,
            decision=result.decision.value,
            provider=provider,
            model=model,
            result=result.model_dump(mode="json"),
            approved_concept=approved_concept.model_dump(mode="json"),
        )
        self._session.add(row)
        await self._session.flush()

        accepted_slot = None if result.decision.value == "MERGE" else result.decision.value
        if accepted_slot:
            candidates = await self._session.execute(
                select(m.ConceptCandidateRecord).where(
                    m.ConceptCandidateRecord.batch_id == batch_id,
                    m.ConceptCandidateRecord.slot == accepted_slot,
                )
            )
            for candidate_row in candidates.scalars():
                candidate_row.accepted = True
        return row.id


class SQLAlchemySeriesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_series(
        self, project_id: str, brief: CreativeBrief, approved_concept: ConceptCandidate
    ) -> SeriesRecord:
        row = m.Series(
            project_id=project_id,
            title=approved_concept.title,
            logline=approved_concept.logline,
            genre=approved_concept.genre,
            target_audience=brief.target_audience,
            episode_count_target=brief.episode_count,
            episode_duration_target_seconds=brief.episode_duration_seconds,
            status="draft",
        )
        self._session.add(row)
        await self._session.flush()
        return SeriesRecord(
            id=row.id,
            project_id=row.project_id,
            title=row.title,
            logline=row.logline,
            genre=row.genre,
            target_audience=row.target_audience,
            episode_count_target=row.episode_count_target,
            episode_duration_target_seconds=row.episode_duration_target_seconds,
            status=row.status,
        )

    async def get_series(self, series_id: str) -> SeriesRecord | None:
        row = await self._session.get(m.Series, series_id)
        if row is None:
            return None
        return SeriesRecord(
            id=row.id,
            project_id=row.project_id,
            title=row.title,
            logline=row.logline,
            genre=row.genre,
            target_audience=row.target_audience,
            episode_count_target=row.episode_count_target,
            episode_duration_target_seconds=row.episode_duration_target_seconds,
            status=row.status,
        )

    async def save_bible(self, series_id: str, bible: SeriesBible) -> None:
        existing = await self._session.execute(
            select(m.SeriesBible).where(m.SeriesBible.series_id == series_id)
        )
        row = existing.scalar_one_or_none()
        if row is None:
            row = m.SeriesBible(series_id=series_id)
            self._session.add(row)
        row.premise = bible.premise
        row.central_dramatic_question = bible.central_dramatic_question
        row.protagonist_objective = bible.protagonist_objective
        row.primary_opposition = bible.primary_opposition
        row.emotional_engine = bible.emotional_engine
        row.themes = bible.themes
        row.world_rules = bible.world_rules
        row.central_secret = bible.central_secret
        row.ending_target = bible.ending_target
        row.prohibited_contradictions = bible.prohibited_contradictions
        row.locked_facts = bible.locked_facts

        series_row = await self._session.get(m.Series, series_id)
        if series_row is not None:
            series_row.title = bible.title
            series_row.logline = bible.logline
            series_row.genre = bible.genres
            series_row.tone = bible.tone
            series_row.target_audience = bible.target_audience
            series_row.episode_count_target = bible.episode_count
            series_row.episode_duration_target_seconds = bible.episode_duration_seconds
            series_row.status = "bible_approved"
        await self._session.flush()

    async def get_bible(self, series_id: str) -> SeriesBible | None:
        bible_result = await self._session.execute(
            select(m.SeriesBible).where(m.SeriesBible.series_id == series_id)
        )
        bible_row = bible_result.scalar_one_or_none()
        series_row = await self._session.get(m.Series, series_id)
        if bible_row is None or series_row is None:
            return None
        return SeriesBible(
            title=series_row.title,
            logline=series_row.logline,
            genres=series_row.genre,
            tone=series_row.tone,
            target_audience=series_row.target_audience,
            episode_count=series_row.episode_count_target,
            episode_duration_seconds=series_row.episode_duration_target_seconds,
            premise=bible_row.premise,
            themes=bible_row.themes,
            emotional_engine=bible_row.emotional_engine,
            central_dramatic_question=bible_row.central_dramatic_question,
            protagonist_objective=bible_row.protagonist_objective,
            primary_opposition=bible_row.primary_opposition,
            world_rules=bible_row.world_rules,
            central_secret=bible_row.central_secret,
            ending_target=bible_row.ending_target,
            prohibited_contradictions=bible_row.prohibited_contradictions,
            locked_facts=bible_row.locked_facts,
        )

    async def save_cast(self, series_id: str, cast: CharacterCast) -> None:
        for character in cast.characters:
            row = await self._session.get(m.Character, character.id)
            if row is None:
                row = m.Character(id=character.id, series_id=series_id)
                self._session.add(row)
            row.name = character.name
            row.role = character.role
            row.age = character.age
            row.description = character.description
            row.personality = character.personality
            row.goal = character.goal
            row.fear = character.fear
            row.flaw = character.flaw
            row.secret = character.secret
            row.character_dna = character.character_dna.model_dump(mode="json")
            row.visual_identity_id = character.visual_identity_id
            row.voice_identity_id = character.voice_identity_id
            row.status = character.status

        for rel in cast.relationships:
            row = m.RelationshipRecord(
                series_id=series_id,
                source_character_id=rel.source_character_id,
                target_character_id=rel.target_character_id,
                relationship_type=rel.relationship_type,
                public_status=rel.public_status,
                private_status=rel.private_status,
                trust_level=rel.trust_level,
                romantic_state=rel.romantic_state,
                valid_from_episode=rel.valid_from_episode,
                valid_to_episode=rel.valid_to_episode,
            )
            self._session.add(row)
        await self._session.flush()

    async def get_cast(self, series_id: str) -> CharacterCast:
        char_rows = await self._session.execute(
            select(m.Character).where(m.Character.series_id == series_id)
        )
        rel_rows = await self._session.execute(
            select(m.RelationshipRecord).where(m.RelationshipRecord.series_id == series_id)
        )
        characters = [
            Character(
                id=row.id,
                name=row.name,
                role=row.role,
                age=row.age,
                description=row.description,
                personality=row.personality,
                goal=row.goal,
                fear=row.fear,
                flaw=row.flaw,
                secret=row.secret,
                character_dna=row.character_dna,
                visual_identity_id=row.visual_identity_id,
                voice_identity_id=row.voice_identity_id,
                status=row.status,
            )
            for row in char_rows.scalars()
        ]
        relationships = [
            RelationshipState(
                source_character_id=row.source_character_id,
                target_character_id=row.target_character_id,
                relationship_type=row.relationship_type,
                public_status=row.public_status,
                private_status=row.private_status,
                trust_level=row.trust_level,
                romantic_state=row.romantic_state,
                valid_from_episode=row.valid_from_episode,
                valid_to_episode=row.valid_to_episode,
            )
            for row in rel_rows.scalars()
        ]
        return CharacterCast(characters=characters, relationships=relationships)


def _season_plan_record(row: m.SeasonPlanRecord) -> SeasonPlanRecord:
    return SeasonPlanRecord(
        id=row.id,
        series_id=row.series_id,
        version=row.version,
        status=row.status,
        plan=SeasonPlan.model_validate(row.plan),
        qc_status=row.qc_status,
        qc_score=row.qc_score,
        qc_reasons=row.qc_reasons,
    )


class SQLAlchemySeasonRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_plan(self, series_id: str, plan: SeasonPlan, qc: QCResult) -> SeasonPlanRecord:
        existing = await self._session.execute(
            select(m.SeasonPlanRecord.version)
            .where(m.SeasonPlanRecord.series_id == series_id)
            .order_by(m.SeasonPlanRecord.version.desc())
            .limit(1)
        )
        last_version = existing.scalar_one_or_none() or 0
        row = m.SeasonPlanRecord(
            series_id=series_id,
            version=last_version + 1,
            status="draft",
            plan=plan.model_dump(mode="json"),
            qc_status=qc.status.value,
            qc_score=qc.score,
            qc_reasons=qc.reasons,
        )
        self._session.add(row)
        await self._session.flush()
        return _season_plan_record(row)

    async def get_current_plan(self, series_id: str) -> SeasonPlanRecord | None:
        approved = await self._session.execute(
            select(m.SeasonPlanRecord)
            .where(m.SeasonPlanRecord.series_id == series_id, m.SeasonPlanRecord.status == "approved")
            .order_by(m.SeasonPlanRecord.version.desc())
            .limit(1)
        )
        row = approved.scalar_one_or_none()
        if row is None:
            latest = await self._session.execute(
                select(m.SeasonPlanRecord)
                .where(m.SeasonPlanRecord.series_id == series_id)
                .order_by(m.SeasonPlanRecord.version.desc())
                .limit(1)
            )
            row = latest.scalar_one_or_none()
        return _season_plan_record(row) if row is not None else None

    async def get_version(self, series_id: str, version: int) -> SeasonPlanRecord | None:
        result = await self._session.execute(
            select(m.SeasonPlanRecord).where(
                m.SeasonPlanRecord.series_id == series_id, m.SeasonPlanRecord.version == version
            )
        )
        row = result.scalar_one_or_none()
        return _season_plan_record(row) if row is not None else None

    async def list_versions(self, series_id: str) -> list[SeasonPlanRecord]:
        result = await self._session.execute(
            select(m.SeasonPlanRecord)
            .where(m.SeasonPlanRecord.series_id == series_id)
            .order_by(m.SeasonPlanRecord.version)
        )
        return [_season_plan_record(row) for row in result.scalars()]

    async def approve_version(self, series_id: str, version: int) -> SeasonPlanRecord:
        result = await self._session.execute(
            select(m.SeasonPlanRecord).where(
                m.SeasonPlanRecord.series_id == series_id, m.SeasonPlanRecord.version == version
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ValueError(f"season plan version {version} not found for series {series_id}")
        row.status = "approved"
        await self._session.flush()
        return _season_plan_record(row)


def _episode_record(row: m.Episode) -> EpisodeRecord:
    return EpisodeRecord(
        id=row.id,
        series_id=row.series_id,
        episode_number=row.episode_number,
        status=row.status,
        version=row.version,
        outline=EpisodeOutline.model_validate(row.outline),
        script=EpisodeScript.model_validate(row.script) if row.script else None,
    )


class SQLAlchemyEpisodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_outline(self, series_id: str, outline: EpisodeOutline) -> EpisodeRecord:
        existing = await self._session.execute(
            select(m.Episode).where(
                m.Episode.series_id == series_id, m.Episode.episode_number == outline.episode_number
            )
        )
        row = existing.scalar_one_or_none()
        if row is None:
            row = m.Episode(series_id=series_id, episode_number=outline.episode_number)
            self._session.add(row)
        row.title = outline.title
        row.objective = outline.objective
        row.opening_hook = outline.opening_hook
        row.central_conflict = outline.conflict
        row.turn = outline.turn
        row.reveal = outline.reveal
        row.cliffhanger_type = outline.cliffhanger.type.value
        row.cliffhanger = outline.cliffhanger.event
        row.duration_target_seconds = outline.duration_target_seconds
        row.outline = outline.model_dump(mode="json")
        row.status = "outlined"
        await self._session.flush()
        return _episode_record(row)

    async def save_script(self, episode_id: str, script: EpisodeScript) -> None:
        row = await self._session.get(m.Episode, episode_id)
        if row is None:
            raise ValueError(f"episode {episode_id} not found")
        # A second save_script call for the same episode is a regeneration -
        # bump the lightweight version counter (Module 02 "idempotent/
        # versioned reruns"). Full script history is not kept; QualityReport
        # rows already preserve the per-attempt audit trail (ADR-019).
        if row.script is not None:
            row.version += 1
        row.script = script.model_dump(mode="json")
        row.status = "scripted"
        await self._session.flush()

    async def save_shot_plan(self, episode_id: str, plan: EpisodeShotPlan) -> None:
        await self._session.execute(delete(m.Scene).where(m.Scene.episode_id == episode_id))
        for scene in plan.scenes:
            scene_row = m.Scene(
                episode_id=episode_id,
                scene_number=scene.scene_number,
                location=scene.location,
                time_of_day=scene.time_of_day,
                characters=scene.characters,
                objective=scene.objective,
                conflict=scene.conflict,
                outcome=scene.outcome,
            )
            self._session.add(scene_row)
            await self._session.flush()
            for shot in scene.shots:
                shot_row = m.Shot(
                    scene_id=scene_row.id,
                    shot_number=shot.shot_number,
                    duration_seconds=shot.duration_seconds,
                    character_ids=shot.character_ids,
                    narrative_function=shot.narrative_function,
                    action=shot.action,
                    dialogue=shot.dialogue,
                    camera=shot.camera.model_dump(mode="json"),
                    visual=shot.visual.model_dump(mode="json"),
                    blocking=shot.blocking,
                    references=shot.references.model_dump(mode="json"),
                    micro_beats=[mb.model_dump(mode="json") for mb in shot.micro_beats],
                    audio_mode=shot.audio_mode.value,
                    continuity_requirements=shot.continuity_requirements,
                    continuity_group=shot.continuity_group,
                    provider_requirements=shot.provider_requirements.model_dump(mode="json"),
                    generation_status=shot.generation_status,
                )
                self._session.add(shot_row)
        row = await self._session.get(m.Episode, episode_id)
        if row is not None:
            row.status = "shot_planned"
        await self._session.flush()

    async def get_shot_plan(self, episode_id: str) -> EpisodeShotPlan | None:
        episode_row = await self._session.get(m.Episode, episode_id)
        if episode_row is None:
            return None
        scene_rows = await self._session.execute(
            select(m.Scene).where(m.Scene.episode_id == episode_id).order_by(m.Scene.scene_number)
        )
        scenes: list[SceneDTO] = []
        for scene_row in scene_rows.scalars():
            shot_rows = await self._session.execute(
                select(m.Shot).where(m.Shot.scene_id == scene_row.id).order_by(m.Shot.shot_number)
            )
            shots = [
                ShotDTO(
                    shot_number=sr.shot_number,
                    scene_number=scene_row.scene_number,
                    narrative_function=sr.narrative_function,
                    character_ids=sr.character_ids,
                    dialogue=sr.dialogue,
                    action=sr.action,
                    duration_seconds=sr.duration_seconds,
                    camera=sr.camera,
                    visual=sr.visual,
                    blocking=sr.blocking,
                    references=sr.references,
                    micro_beats=sr.micro_beats,
                    audio_mode=sr.audio_mode,
                    continuity_requirements=sr.continuity_requirements,
                    continuity_group=sr.continuity_group,
                    provider_requirements=sr.provider_requirements,
                    generation_status=sr.generation_status,
                )
                for sr in shot_rows.scalars()
            ]
            scenes.append(
                SceneDTO(
                    scene_number=scene_row.scene_number,
                    location=scene_row.location,
                    time_of_day=scene_row.time_of_day,
                    characters=scene_row.characters,
                    objective=scene_row.objective,
                    conflict=scene_row.conflict,
                    outcome=scene_row.outcome,
                    shots=shots,
                )
            )
        if not scenes:
            return None
        return EpisodeShotPlan(episode_number=episode_row.episode_number, scenes=scenes)

    async def save_quality_report(self, episode_id: str, result: QCResult) -> None:
        row = m.QualityReport(
            episode_id=episode_id,
            gate=result.gate,
            status=result.status.value,
            score=result.score,
            reasons=result.reasons,
            repair_recommendation=result.repair_recommendation,
        )
        self._session.add(row)
        await self._session.flush()

    async def save_canon_event(self, episode_id: str, event: CanonEvent) -> None:
        row = m.EpisodeStateChange(
            episode_id=episode_id,
            change_type=event.change_type.value,
            description=event.description,
            payload=event.payload,
            committed=event.committed,
        )
        self._session.add(row)
        await self._session.flush()

    async def invalidate_canon_events(self, episode_id: str) -> None:
        rows = await self._session.execute(
            select(m.EpisodeStateChange).where(m.EpisodeStateChange.episode_id == episode_id)
        )
        for row in rows.scalars():
            row.committed = False
        await self._session.flush()

    async def list_canon_events(
        self, series_id: str, before_episode: int | None = None
    ) -> list[CanonEvent]:
        query = (
            select(m.EpisodeStateChange, m.Episode.episode_number)
            .join(m.Episode, m.EpisodeStateChange.episode_id == m.Episode.id)
            .where(m.Episode.series_id == series_id, m.EpisodeStateChange.committed == True)  # noqa: E712
        )
        if before_episode is not None:
            query = query.where(m.Episode.episode_number < before_episode)
        query = query.order_by(m.Episode.episode_number)
        rows = await self._session.execute(query)
        return [
            CanonEvent(
                change_type=change.change_type,
                episode_number=episode_number,
                description=change.description,
                payload=change.payload,
                committed=change.committed,
            )
            for change, episode_number in rows.all()
        ]

    async def set_status(self, episode_id: str, status: str) -> None:
        row = await self._session.get(m.Episode, episode_id)
        if row is None:
            raise ValueError(f"episode {episode_id} not found")
        row.status = status
        await self._session.flush()

    async def list_by_series(self, series_id: str) -> list[EpisodeRecord]:
        rows = await self._session.execute(
            select(m.Episode).where(m.Episode.series_id == series_id).order_by(m.Episode.episode_number)
        )
        return [_episode_record(row) for row in rows.scalars()]

    async def get(self, episode_id: str) -> EpisodeRecord | None:
        row = await self._session.get(m.Episode, episode_id)
        if row is None:
            return None
        return _episode_record(row)

    async def get_by_number(self, series_id: str, episode_number: int) -> EpisodeRecord | None:
        result = await self._session.execute(
            select(m.Episode).where(
                m.Episode.series_id == series_id, m.Episode.episode_number == episode_number
            )
        )
        row = result.scalar_one_or_none()
        return _episode_record(row) if row is not None else None


class SQLAlchemyJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, project_id: str, stage: JobStage) -> JobRecord:
        row = m.GenerationJob(project_id=project_id, stage=stage.value, status=JobStatus.QUEUED.value)
        self._session.add(row)
        await self._session.flush()
        return JobRecord(id=row.id, project_id=row.project_id, stage=stage, status=JobStatus.QUEUED)

    async def start(self, job_id: str, provider: str = "", model: str = "") -> None:
        row = await self._session.get(m.GenerationJob, job_id)
        if row is None:
            raise ValueError(f"job {job_id} not found")
        row.status = JobStatus.RUNNING.value
        row.provider = provider
        row.model = model
        row.started_at = utcnow()
        await self._session.flush()

    async def succeed(self, job_id: str) -> None:
        row = await self._session.get(m.GenerationJob, job_id)
        if row is None:
            raise ValueError(f"job {job_id} not found")
        row.status = JobStatus.SUCCEEDED.value
        row.finished_at = utcnow()
        await self._session.flush()

    async def fail(self, job_id: str, error: str) -> None:
        row = await self._session.get(m.GenerationJob, job_id)
        if row is None:
            raise ValueError(f"job {job_id} not found")
        row.status = JobStatus.FAILED.value
        row.error = error
        row.finished_at = utcnow()
        await self._session.flush()

    async def get(self, job_id: str) -> JobRecord | None:
        row = await self._session.get(m.GenerationJob, job_id)
        if row is None:
            return None
        return JobRecord(
            id=row.id,
            project_id=row.project_id,
            stage=JobStage(row.stage),
            status=JobStatus(row.status),
            provider=row.provider,
            model=row.model,
            attempt=row.attempt,
            error=row.error,
        )
