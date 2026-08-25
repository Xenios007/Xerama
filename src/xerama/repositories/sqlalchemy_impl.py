"""SQLAlchemy-backed implementations of the repository Protocols in
`interfaces.py`. Pipeline/service code should type-hint against the
Protocols, not import this module directly, so a future backend swap stays
localized (ADR-021)."""

from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from xerama.db import models as m
from xerama.db.base import utcnow
from xerama.domain.asset import Asset, AssetOwnership, AssetProvenance, AssetStatus, AssetType
from xerama.domain.brief import CreativeBrief
from xerama.domain.canon import CanonEvent
from xerama.domain.character import (
    Character,
    CharacterCast,
    CharacterProvenance,
    PhysicalStateVariant,
    RelationshipState,
    WardrobeVariant,
)
from xerama.domain.enums import AudioMode, JobStage, JobStatus, MediaQCDimension, QCStatus
from xerama.domain.episode import EpisodeOutline, EpisodeScript
from xerama.domain.quality import QCResult
from xerama.domain.scene import EpisodeShotPlan, Scene as SceneDTO, Shot as ShotDTO
from xerama.domain.audio_production import ShotAudioProduction
from xerama.domain.analytics import EpisodeMetric
from xerama.domain.cost import CostRecord
from xerama.domain.episode_render import EpisodeRender
from xerama.domain.feedback import HumanFeedback
from xerama.domain.media_qc import MediaQCAttempt
from xerama.domain.music import MusicCue
from xerama.domain.rights import RightsMetadata
from xerama.domain.season import SeasonPlan
from xerama.domain.sound_effect import SoundEffectCue
from xerama.domain.storyboard import Storyboard
from xerama.domain.subtitle import SubtitleCue
from xerama.domain.story import ConceptCandidate, JudgeResult, SeriesBible
from xerama.domain.style_bible import StyleBible
from xerama.domain.video_production import ShotVideoProduction
from xerama.domain.voice import VoiceProfile
from xerama.repositories.interfaces import (
    ConceptCandidateRecord as ConceptCandidateRecordDTO,
    EpisodeRecord,
    JobRecord,
    JudgeDecisionRecord as JudgeDecisionRecordDTO,
    ProjectRecord,
    SeasonPlanRecord,
    SeriesRecord,
)


def _project_record(row: m.Project) -> ProjectRecord:
    return ProjectRecord(
        id=row.id, name=row.name, description=row.description, status=row.status, created_at=row.created_at
    )


class SQLAlchemyProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, name: str, description: str = "") -> ProjectRecord:
        row = m.Project(name=name, description=description)
        self._session.add(row)
        await self._session.flush()
        return _project_record(row)

    async def get(self, project_id: str) -> ProjectRecord | None:
        row = await self._session.get(m.Project, project_id)
        return _project_record(row) if row is not None else None

    async def list_all(self) -> list[ProjectRecord]:
        result = await self._session.execute(select(m.Project).order_by(m.Project.created_at.desc()))
        return [_project_record(row) for row in result.scalars()]

    async def update(
        self, project_id: str, name: str | None = None, description: str | None = None
    ) -> ProjectRecord:
        row = await self._session.get(m.Project, project_id)
        if row is None:
            raise ValueError(f"project {project_id} not found")
        if row.status == "archived":
            raise PermissionError(f"project {project_id} is archived - cannot edit")
        if name is not None:
            row.name = name
        if description is not None:
            row.description = description
        await self._session.flush()
        return _project_record(row)

    async def archive(self, project_id: str) -> ProjectRecord:
        row = await self._session.get(m.Project, project_id)
        if row is None:
            raise ValueError(f"project {project_id} not found")
        row.status = "archived"
        await self._session.flush()
        return _project_record(row)


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

    async def list_candidates(self, project_id: str) -> list[ConceptCandidateRecordDTO]:
        result = await self._session.execute(
            select(m.ConceptCandidateRecord)
            .where(m.ConceptCandidateRecord.project_id == project_id)
            .order_by(m.ConceptCandidateRecord.created_at)
        )
        return [
            ConceptCandidateRecordDTO(
                id=row.id,
                project_id=row.project_id,
                batch_id=row.batch_id,
                slot=row.slot,
                provider=row.provider,
                model=row.model,
                candidate=ConceptCandidate.model_validate(row.candidate),
                accepted=row.accepted,
                created_at=row.created_at,
            )
            for row in result.scalars()
        ]

    async def list_judge_decisions(self, project_id: str) -> list[JudgeDecisionRecordDTO]:
        result = await self._session.execute(
            select(m.JudgeDecisionRecord)
            .where(m.JudgeDecisionRecord.project_id == project_id)
            .order_by(m.JudgeDecisionRecord.created_at)
        )
        return [
            JudgeDecisionRecordDTO(
                id=row.id,
                project_id=row.project_id,
                batch_id=row.batch_id,
                decision=row.decision,
                provider=row.provider,
                model=row.model,
                result=JudgeResult.model_validate(row.result),
                approved_concept=ConceptCandidate.model_validate(row.approved_concept),
                created_at=row.created_at,
            )
            for row in result.scalars()
        ]


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

    async def list_by_project(self, project_id: str) -> list[SeriesRecord]:
        result = await self._session.execute(
            select(m.Series).where(m.Series.project_id == project_id)
        )
        return [
            SeriesRecord(
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
            for row in result.scalars()
        ]

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
        characters = [_character(row) for row in char_rows.scalars()]
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
                    production_priority=shot.production_priority.value,
                    action=shot.action,
                    dialogue=shot.dialogue,
                    camera=shot.camera.model_dump(mode="json"),
                    visual=shot.visual.model_dump(mode="json"),
                    blocking=shot.blocking,
                    blocking_plan=shot.blocking_plan.model_dump(mode="json") if shot.blocking_plan else None,
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
                    production_priority=sr.production_priority,
                    character_ids=sr.character_ids,
                    dialogue=sr.dialogue,
                    action=sr.action,
                    duration_seconds=sr.duration_seconds,
                    camera=sr.camera,
                    visual=sr.visual,
                    blocking=sr.blocking,
                    blocking_plan=sr.blocking_plan,
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

    async def list_quality_reports(self, episode_id: str) -> list[QCResult]:
        result = await self._session.execute(
            select(m.QualityReport)
            .where(m.QualityReport.episode_id == episode_id)
            .order_by(m.QualityReport.created_at)
        )
        return [
            QCResult(
                gate=row.gate,
                status=QCStatus(row.status),
                score=row.score,
                reasons=row.reasons,
                repair_recommendation=row.repair_recommendation,
            )
            for row in result.scalars()
        ]

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


def _job_record(row: m.GenerationJob) -> JobRecord:
    return JobRecord(
        id=row.id,
        project_id=row.project_id,
        stage=JobStage(row.stage),
        status=JobStatus(row.status),
        provider=row.provider,
        model=row.model,
        attempt=row.attempt,
        error=row.error,
        priority=row.priority,
        payload=row.payload,
        depends_on_job_id=row.depends_on_job_id,
        max_attempts=row.max_attempts,
        lease_owner=row.lease_owner,
        result_asset_ids=row.result_asset_ids,
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


# MODULE-052 - stages that only ever make sense one-at-a-time per
# (project, series): running a second concurrent CONCEPT_GENERATION or
# SEASON_PLAN job would race against the first, not add throughput.
# Per-episode stages are deliberately excluded - see `enqueue`'s docstring.
_SINGLETON_PER_PROJECT_SERIES_STAGES = frozenset(
    {
        JobStage.CONCEPT_GENERATION,
        JobStage.JUDGE,
        JobStage.CONCEPT_MERGE,
        JobStage.SERIES_BIBLE,
        JobStage.CHARACTERS,
        JobStage.SEASON_PLAN,
    }
)

# Exponential backoff for requeued job attempts, capped at 5 minutes -
# MODULE-043 "bounded attempts/backoff".
_BACKOFF_BASE_SECONDS = 5
_BACKOFF_MAX_SECONDS = 300


def _backoff_seconds(attempt: int) -> int:
    return min(_BACKOFF_MAX_SECONDS, _BACKOFF_BASE_SECONDS * (2 ** max(0, attempt - 1)))


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
        return _job_record(row) if row is not None else None

    async def list_by_project(self, project_id: str) -> list[JobRecord]:
        result = await self._session.execute(
            select(m.GenerationJob)
            .where(m.GenerationJob.project_id == project_id)
            .order_by(m.GenerationJob.created_at.desc())
        )
        return [_job_record(row) for row in result.scalars()]

    async def list_filtered(
        self,
        project_id: str | None = None,
        stage: JobStage | None = None,
        status: JobStatus | None = None,
    ) -> list[JobRecord]:
        query = select(m.GenerationJob)
        if project_id is not None:
            query = query.where(m.GenerationJob.project_id == project_id)
        if stage is not None:
            query = query.where(m.GenerationJob.stage == stage.value)
        if status is not None:
            query = query.where(m.GenerationJob.status == status.value)
        query = query.order_by(m.GenerationJob.created_at.desc())
        result = await self._session.execute(query)
        return [_job_record(row) for row in result.scalars()]

    # --- Job-queue methods (MODULE-041) ---

    async def enqueue(
        self,
        project_id: str,
        stage: JobStage,
        payload: dict,
        priority: int = 0,
        series_id: str | None = None,
        depends_on_job_id: str | None = None,
        scheduled_at: datetime | None = None,
        max_attempts: int = 3,
    ) -> JobRecord:
        # MODULE-052 - "prevent duplicate incompatible runs": only for
        # stages that are meaningfully singular per (project, series) at a
        # time - `GenerationJob` has no `episode_id` column, so per-episode
        # stages (script/shots/etc.) can't be safely deduplicated this way
        # without risking a false-positive block on two *different*
        # episodes' legitimate concurrent jobs; documented scope limit.
        if stage in _SINGLETON_PER_PROJECT_SERIES_STAGES:
            existing = await self._session.execute(
                select(m.GenerationJob).where(
                    m.GenerationJob.project_id == project_id,
                    m.GenerationJob.series_id == series_id,
                    m.GenerationJob.stage == stage.value,
                    m.GenerationJob.status.in_(
                        [JobStatus.QUEUED.value, JobStatus.RUNNING.value, JobStatus.RETRYING.value]
                    ),
                )
            )
            if existing.scalars().first() is not None:
                raise ValueError(
                    f"a {stage.value} job is already in flight for this project/series - "
                    "wait for it to finish or cancel it first"
                )
        row = m.GenerationJob(
            project_id=project_id,
            series_id=series_id,
            stage=stage.value,
            status=JobStatus.QUEUED.value,
            priority=priority,
            payload=payload,
            depends_on_job_id=depends_on_job_id,
            scheduled_at=scheduled_at or utcnow(),
            max_attempts=max_attempts,
        )
        self._session.add(row)
        await self._session.flush()
        return _job_record(row)

    async def claim(self, worker_id: str, lease_seconds: int = 60) -> JobRecord | None:
        now = utcnow()
        result = await self._session.execute(
            select(m.GenerationJob)
            .where(
                m.GenerationJob.status == JobStatus.QUEUED.value,
                m.GenerationJob.scheduled_at <= now,
            )
            .order_by(m.GenerationJob.priority.desc(), m.GenerationJob.created_at.asc())
        )
        for row in result.scalars():
            if row.depends_on_job_id:
                dependency = await self._session.get(m.GenerationJob, row.depends_on_job_id)
                if dependency is not None and dependency.status != JobStatus.SUCCEEDED.value:
                    continue  # dependency not satisfied yet - skip, don't claim
            # Optimistic claim: a plain UPDATE...WHERE guarded on the state
            # we just observed. Two workers racing both attempt this; only
            # the one whose WHERE clause still matches actually updates the
            # row (SQLAlchemy reports it via rowcount), so the loser simply
            # doesn't win instead of double-processing the job.
            claim_result = await self._session.execute(
                m.GenerationJob.__table__.update()
                .where(
                    m.GenerationJob.id == row.id,
                    m.GenerationJob.status == JobStatus.QUEUED.value,
                )
                .values(
                    status=JobStatus.RUNNING.value,
                    lease_owner=worker_id,
                    lease_expires_at=now + timedelta(seconds=lease_seconds),
                    started_at=now,
                )
            )
            if claim_result.rowcount == 1:
                # The raw Core UPDATE above bypassed the ORM, so `row`
                # (identity-mapped from the SELECT) still holds pre-update
                # values in memory. `refresh()` is the async-safe way to
                # reload it from the DB - setting the attributes directly
                # instead would create a "round trip" in SQLAlchemy's dirty-
                # tracking once a later fail_job_attempt() sets `status`
                # back toward its originally-loaded value, causing that
                # attribute to be silently dropped from the next flush's
                # UPDATE (SQLAlchemy compares against last-loaded value, not
                # intermediate unflushed writes).
                await self._session.refresh(row)
                return _job_record(row)
        return None

    async def heartbeat(self, job_id: str, worker_id: str, lease_seconds: int = 60) -> None:
        row = await self._session.get(m.GenerationJob, job_id)
        if row is None:
            raise ValueError(f"job {job_id} not found")
        if row.lease_owner != worker_id:
            raise PermissionError(f"job {job_id} is not leased by worker {worker_id!r}")
        row.lease_expires_at = utcnow() + timedelta(seconds=lease_seconds)
        await self._session.flush()

    async def succeed_job(self, job_id: str, result_asset_ids: list[str] | None = None) -> JobRecord:
        row = await self._session.get(m.GenerationJob, job_id)
        if row is None:
            raise ValueError(f"job {job_id} not found")
        row.status = JobStatus.SUCCEEDED.value
        row.result_asset_ids = result_asset_ids or []
        row.finished_at = utcnow()
        row.lease_owner = None
        row.lease_expires_at = None
        await self._session.flush()
        return _job_record(row)

    async def fail_job_attempt(self, job_id: str, error: str, retriable: bool) -> JobRecord:
        row = await self._session.get(m.GenerationJob, job_id)
        if row is None:
            raise ValueError(f"job {job_id} not found")
        row.error = error
        row.lease_owner = None
        row.lease_expires_at = None
        if retriable and row.attempt < row.max_attempts:
            row.attempt += 1
            row.status = JobStatus.QUEUED.value
            row.scheduled_at = utcnow() + timedelta(seconds=_backoff_seconds(row.attempt))
        else:
            row.status = JobStatus.FAILED.value  # dead-letter - operator-visible via `error`
            row.finished_at = utcnow()
        await self._session.flush()
        return _job_record(row)

    async def cancel(self, job_id: str) -> JobRecord:
        row = await self._session.get(m.GenerationJob, job_id)
        if row is None:
            raise ValueError(f"job {job_id} not found")
        if row.status not in (JobStatus.SUCCEEDED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value):
            row.status = JobStatus.CANCELLED.value
            row.finished_at = utcnow()
            row.lease_owner = None
            row.lease_expires_at = None
            await self._session.flush()
        return _job_record(row)

    async def recover_abandoned(self, now: datetime | None = None) -> list[JobRecord]:
        now = now or utcnow()
        result = await self._session.execute(
            select(m.GenerationJob).where(
                m.GenerationJob.status == JobStatus.RUNNING.value,
                m.GenerationJob.lease_expires_at.is_not(None),
                m.GenerationJob.lease_expires_at < now,
            )
        )
        recovered = []
        for row in result.scalars():
            row.status = JobStatus.QUEUED.value
            row.lease_owner = None
            row.lease_expires_at = None
            recovered.append(row)
        await self._session.flush()
        return [_job_record(row) for row in recovered]

    async def list_queued(self, stage: JobStage | None = None) -> list[JobRecord]:
        query = select(m.GenerationJob).where(m.GenerationJob.status == JobStatus.QUEUED.value)
        if stage is not None:
            query = query.where(m.GenerationJob.stage == stage.value)
        query = query.order_by(m.GenerationJob.priority.desc(), m.GenerationJob.created_at.asc())
        result = await self._session.execute(query)
        return [_job_record(row) for row in result.scalars()]

    async def list_failed(self, project_id: str | None = None) -> list[JobRecord]:
        query = select(m.GenerationJob).where(m.GenerationJob.status == JobStatus.FAILED.value)
        if project_id is not None:
            query = query.where(m.GenerationJob.project_id == project_id)
        result = await self._session.execute(query)
        return [_job_record(row) for row in result.scalars()]


def _asset(row: m.Asset) -> Asset:
    return Asset(
        id=row.id,
        type=AssetType(row.type),
        status=AssetStatus(row.status),
        storage_path=row.storage_path,
        content_hash=row.content_hash,
        mime_type=row.mime_type,
        size_bytes=row.size_bytes,
        width=row.width,
        height=row.height,
        duration_seconds=row.duration_seconds,
        ownership=AssetOwnership(
            project_id=row.project_id,
            series_id=row.series_id,
            episode_id=row.episode_id,
            character_id=row.character_id,
            scene_number=row.scene_number,
            shot_number=row.shot_number,
        ),
        provenance=AssetProvenance.model_validate(row.provenance),
        take_number=row.take_number,
        rejection_reason=row.rejection_reason,
        created_at=row.created_at,
    )


class SQLAlchemyAssetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        asset_type: AssetType,
        storage_path: str,
        content_hash: str,
        ownership: AssetOwnership,
        provenance: AssetProvenance | None = None,
        mime_type: str = "",
        size_bytes: int = 0,
        width: int | None = None,
        height: int | None = None,
        duration_seconds: float | None = None,
        take_number: int = 1,
    ) -> Asset:
        row = m.Asset(
            type=asset_type.value,
            storage_path=storage_path,
            content_hash=content_hash,
            mime_type=mime_type,
            size_bytes=size_bytes,
            width=width,
            height=height,
            duration_seconds=duration_seconds,
            project_id=ownership.project_id,
            series_id=ownership.series_id,
            episode_id=ownership.episode_id,
            character_id=ownership.character_id,
            scene_number=ownership.scene_number,
            shot_number=ownership.shot_number,
            provenance=(provenance or AssetProvenance()).model_dump(mode="json"),
            take_number=take_number,
        )
        self._session.add(row)
        await self._session.flush()
        return _asset(row)

    async def get(self, asset_id: str) -> Asset | None:
        row = await self._session.get(m.Asset, asset_id)
        return _asset(row) if row is not None else None

    async def get_by_hash(self, content_hash: str) -> Asset | None:
        result = await self._session.execute(
            select(m.Asset).where(m.Asset.content_hash == content_hash)
        )
        row = result.scalars().first()
        return _asset(row) if row is not None else None

    async def list_by_ownership(
        self,
        project_id: str,
        series_id: str | None = None,
        episode_id: str | None = None,
        character_id: str | None = None,
        scene_number: int | None = None,
        shot_number: int | None = None,
        asset_type: AssetType | None = None,
        status: AssetStatus | None = None,
    ) -> list[Asset]:
        query = select(m.Asset).where(m.Asset.project_id == project_id)
        if series_id is not None:
            query = query.where(m.Asset.series_id == series_id)
        if episode_id is not None:
            query = query.where(m.Asset.episode_id == episode_id)
        if character_id is not None:
            query = query.where(m.Asset.character_id == character_id)
        if scene_number is not None:
            query = query.where(m.Asset.scene_number == scene_number)
        if shot_number is not None:
            query = query.where(m.Asset.shot_number == shot_number)
        if asset_type is not None:
            query = query.where(m.Asset.type == asset_type.value)
        if status is not None:
            query = query.where(m.Asset.status == status.value)
        query = query.order_by(m.Asset.created_at)
        result = await self._session.execute(query)
        return [_asset(row) for row in result.scalars()]

    async def list_all(self) -> list[Asset]:
        result = await self._session.execute(select(m.Asset).order_by(m.Asset.created_at))
        return [_asset(row) for row in result.scalars()]

    async def set_status(
        self, asset_id: str, status: AssetStatus, rejection_reason: str = ""
    ) -> Asset:
        row = await self._session.get(m.Asset, asset_id)
        if row is None:
            raise ValueError(f"asset {asset_id} not found")
        row.status = status.value
        row.rejection_reason = rejection_reason if status == AssetStatus.REJECTED else ""
        await self._session.flush()
        return _asset(row)

    async def delete(self, asset_id: str) -> None:
        row = await self._session.get(m.Asset, asset_id)
        if row is not None:
            await self._session.delete(row)
            await self._session.flush()


def _character(row: m.Character) -> Character:
    return Character(
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
        reference_pack=row.reference_pack,
        identity_provenance=CharacterProvenance.model_validate(row.identity_provenance)
        if row.identity_provenance
        else CharacterProvenance(),
        locked=row.locked,
        version=row.version,
        status=row.status,
    )


def _wardrobe_variant(row: m.CharacterWardrobeVariant) -> WardrobeVariant:
    return WardrobeVariant(
        id=row.id,
        character_id=row.character_id,
        label=row.label,
        reference_asset_ids=row.reference_asset_ids,
        description=row.description,
    )


def _physical_state_variant(row: m.CharacterPhysicalStateVariant) -> PhysicalStateVariant:
    return PhysicalStateVariant(
        id=row.id,
        character_id=row.character_id,
        label=row.label,
        reference_asset_ids=row.reference_asset_ids,
        description=row.description,
    )


class SQLAlchemyCharacterCastingRepository:
    """See Module 05 - single-character identity CRUD/lock/version and
    wardrobe/physical-state variants."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_character(self, character_id: str) -> Character | None:
        row = await self._session.get(m.Character, character_id)
        return _character(row) if row is not None else None

    async def save_character(self, character: Character) -> Character:
        row = await self._session.get(m.Character, character.id)
        if row is None:
            raise ValueError(f"character {character.id} not found")
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
        row.reference_pack = character.reference_pack
        row.identity_provenance = character.identity_provenance.model_dump(mode="json")
        row.locked = character.locked
        row.version = character.version
        row.status = character.status
        await self._session.flush()
        return _character(row)

    async def set_lock(self, character_id: str, locked: bool) -> Character:
        row = await self._session.get(m.Character, character_id)
        if row is None:
            raise ValueError(f"character {character_id} not found")
        row.locked = locked
        await self._session.flush()
        return _character(row)

    async def unlock_and_bump_version(self, character_id: str) -> Character:
        row = await self._session.get(m.Character, character_id)
        if row is None:
            raise ValueError(f"character {character_id} not found")
        row.locked = False
        row.version += 1
        await self._session.flush()
        return _character(row)

    async def create_wardrobe_variant(
        self,
        character_id: str,
        label: str,
        reference_asset_ids: list[str],
        description: str = "",
    ) -> WardrobeVariant:
        row = m.CharacterWardrobeVariant(
            character_id=character_id,
            label=label,
            reference_asset_ids=reference_asset_ids,
            description=description,
        )
        self._session.add(row)
        await self._session.flush()
        return _wardrobe_variant(row)

    async def list_wardrobe_variants(self, character_id: str) -> list[WardrobeVariant]:
        result = await self._session.execute(
            select(m.CharacterWardrobeVariant)
            .where(m.CharacterWardrobeVariant.character_id == character_id)
            .order_by(m.CharacterWardrobeVariant.created_at)
        )
        return [_wardrobe_variant(row) for row in result.scalars()]

    async def create_physical_state_variant(
        self,
        character_id: str,
        label: str,
        reference_asset_ids: list[str],
        description: str = "",
    ) -> PhysicalStateVariant:
        row = m.CharacterPhysicalStateVariant(
            character_id=character_id,
            label=label,
            reference_asset_ids=reference_asset_ids,
            description=description,
        )
        self._session.add(row)
        await self._session.flush()
        return _physical_state_variant(row)

    async def list_physical_state_variants(self, character_id: str) -> list[PhysicalStateVariant]:
        result = await self._session.execute(
            select(m.CharacterPhysicalStateVariant)
            .where(m.CharacterPhysicalStateVariant.character_id == character_id)
            .order_by(m.CharacterPhysicalStateVariant.created_at)
        )
        return [_physical_state_variant(row) for row in result.scalars()]


def _style_bible(row: m.StyleBible) -> StyleBible:
    return StyleBible(
        id=row.id,
        series_id=row.series_id,
        style_asset_id=row.style_asset_id,
        style_dna=row.style_dna,
        palette=row.palette,
        lighting=row.lighting,
        texture=row.texture,
        color_temperature=row.color_temperature,
        composition_rules=row.composition_rules,
        negatives=row.negatives,
        locked=row.locked,
        version=row.version,
    )


class SQLAlchemyStyleBibleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, series_id: str) -> StyleBible:
        result = await self._session.execute(
            select(m.StyleBible).where(m.StyleBible.series_id == series_id)
        )
        row = result.scalars().first()
        if row is None:
            row = m.StyleBible(series_id=series_id)
            self._session.add(row)
            await self._session.flush()
        return _style_bible(row)

    async def save(self, style_bible: StyleBible) -> StyleBible:
        row = await self._session.get(m.StyleBible, style_bible.id)
        if row is None:
            raise ValueError(f"style bible {style_bible.id} not found")
        row.style_asset_id = style_bible.style_asset_id
        row.style_dna = style_bible.style_dna
        row.palette = style_bible.palette
        row.lighting = style_bible.lighting
        row.texture = style_bible.texture
        row.color_temperature = style_bible.color_temperature
        row.composition_rules = style_bible.composition_rules
        row.negatives = style_bible.negatives
        row.locked = style_bible.locked
        row.version = style_bible.version
        await self._session.flush()
        return _style_bible(row)

    async def set_lock(self, series_id: str, locked: bool) -> StyleBible:
        result = await self._session.execute(
            select(m.StyleBible).where(m.StyleBible.series_id == series_id)
        )
        row = result.scalars().first()
        if row is None:
            raise ValueError(f"style bible for series {series_id} not found")
        row.locked = locked
        await self._session.flush()
        return _style_bible(row)

    async def unlock_and_bump_version(self, series_id: str) -> StyleBible:
        result = await self._session.execute(
            select(m.StyleBible).where(m.StyleBible.series_id == series_id)
        )
        row = result.scalars().first()
        if row is None:
            raise ValueError(f"style bible for series {series_id} not found")
        row.locked = False
        row.version += 1
        await self._session.flush()
        return _style_bible(row)


def _storyboard(row: m.Storyboard) -> Storyboard:
    return Storyboard(
        id=row.id,
        episode_id=row.episode_id,
        scene_number=row.scene_number,
        shot_number=row.shot_number,
        status=row.status,
        layout_description=row.layout_description,
        approved_keyframe_asset_id=row.approved_keyframe_asset_id,
        auto_retake_attempts=row.auto_retake_attempts,
        escalated=row.escalated,
    )


class SQLAlchemyStoryboardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(
        self, episode_id: str, scene_number: int, shot_number: int, layout_description: str = ""
    ) -> Storyboard:
        result = await self._session.execute(
            select(m.Storyboard).where(
                m.Storyboard.episode_id == episode_id,
                m.Storyboard.scene_number == scene_number,
                m.Storyboard.shot_number == shot_number,
            )
        )
        row = result.scalars().first()
        if row is None:
            row = m.Storyboard(
                episode_id=episode_id,
                scene_number=scene_number,
                shot_number=shot_number,
                layout_description=layout_description,
            )
            self._session.add(row)
            await self._session.flush()
        return _storyboard(row)

    async def get(self, storyboard_id: str) -> Storyboard | None:
        row = await self._session.get(m.Storyboard, storyboard_id)
        return _storyboard(row) if row is not None else None

    async def approve(self, storyboard_id: str, asset_id: str) -> Storyboard:
        row = await self._session.get(m.Storyboard, storyboard_id)
        if row is None:
            raise ValueError(f"storyboard {storyboard_id} not found")
        row.status = "approved"
        row.approved_keyframe_asset_id = asset_id
        await self._session.flush()
        return _storyboard(row)

    async def list_by_episode(self, episode_id: str) -> list[Storyboard]:
        result = await self._session.execute(
            select(m.Storyboard).where(m.Storyboard.episode_id == episode_id)
        )
        return [_storyboard(row) for row in result.scalars()]

    async def record_retake_attempt(self, storyboard_id: str, escalated: bool = False) -> Storyboard:
        row = await self._session.get(m.Storyboard, storyboard_id)
        if row is None:
            raise ValueError(f"storyboard {storyboard_id} not found")
        row.auto_retake_attempts += 1
        if escalated:
            row.escalated = True
        await self._session.flush()
        return _storyboard(row)


def _video_production(row: m.ShotVideoProduction) -> ShotVideoProduction:
    return ShotVideoProduction(
        id=row.id,
        episode_id=row.episode_id,
        scene_number=row.scene_number,
        shot_number=row.shot_number,
        continuity_group=row.continuity_group,
        status=row.status,
        approved_take_asset_id=row.approved_take_asset_id,
        extracted_last_frame_asset_id=row.extracted_last_frame_asset_id,
        auto_retake_attempts=row.auto_retake_attempts,
        escalated=row.escalated,
    )


class SQLAlchemyVideoProductionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(
        self,
        episode_id: str,
        scene_number: int,
        shot_number: int,
        continuity_group: str | None = None,
    ) -> ShotVideoProduction:
        result = await self._session.execute(
            select(m.ShotVideoProduction).where(
                m.ShotVideoProduction.episode_id == episode_id,
                m.ShotVideoProduction.scene_number == scene_number,
                m.ShotVideoProduction.shot_number == shot_number,
            )
        )
        row = result.scalars().first()
        if row is None:
            row = m.ShotVideoProduction(
                episode_id=episode_id,
                scene_number=scene_number,
                shot_number=shot_number,
                continuity_group=continuity_group,
            )
            self._session.add(row)
            await self._session.flush()
        return _video_production(row)

    async def get(self, production_id: str) -> ShotVideoProduction | None:
        row = await self._session.get(m.ShotVideoProduction, production_id)
        return _video_production(row) if row is not None else None

    async def get_previous_in_continuity_group(
        self, episode_id: str, continuity_group: str, before_scene_number: int, before_shot_number: int
    ) -> ShotVideoProduction | None:
        result = await self._session.execute(
            select(m.ShotVideoProduction).where(
                m.ShotVideoProduction.episode_id == episode_id,
                m.ShotVideoProduction.continuity_group == continuity_group,
            )
        )
        candidates = [
            row
            for row in result.scalars()
            if (row.scene_number, row.shot_number) < (before_scene_number, before_shot_number)
        ]
        if not candidates:
            return None
        latest = max(candidates, key=lambda row: (row.scene_number, row.shot_number))
        return _video_production(latest)

    async def approve(self, production_id: str, asset_id: str) -> ShotVideoProduction:
        row = await self._session.get(m.ShotVideoProduction, production_id)
        if row is None:
            raise ValueError(f"video production {production_id} not found")
        row.status = "approved"
        row.approved_take_asset_id = asset_id
        await self._session.flush()
        return _video_production(row)

    async def set_extracted_last_frame(self, production_id: str, asset_id: str) -> ShotVideoProduction:
        row = await self._session.get(m.ShotVideoProduction, production_id)
        if row is None:
            raise ValueError(f"video production {production_id} not found")
        row.extracted_last_frame_asset_id = asset_id
        await self._session.flush()
        return _video_production(row)

    async def list_by_episode(self, episode_id: str) -> list[ShotVideoProduction]:
        result = await self._session.execute(
            select(m.ShotVideoProduction).where(m.ShotVideoProduction.episode_id == episode_id)
        )
        return [_video_production(row) for row in result.scalars()]

    async def record_retake_attempt(
        self, production_id: str, escalated: bool = False
    ) -> ShotVideoProduction:
        row = await self._session.get(m.ShotVideoProduction, production_id)
        if row is None:
            raise ValueError(f"video production {production_id} not found")
        row.auto_retake_attempts += 1
        if escalated:
            row.escalated = True
        await self._session.flush()
        return _video_production(row)


def _voice_profile(row: m.VoiceProfile) -> VoiceProfile:
    return VoiceProfile(
        id=row.id,
        character_id=row.character_id,
        provider=row.provider,
        provider_voice_id=row.provider_voice_id,
        language=row.language,
        style=row.style,
        pronunciation_dictionary=row.pronunciation_dictionary,
        provenance=CharacterProvenance.model_validate(row.provenance) if row.provenance else CharacterProvenance(),
        locked=row.locked,
        version=row.version,
    )


class SQLAlchemyVoiceProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, character_id: str) -> VoiceProfile:
        result = await self._session.execute(
            select(m.VoiceProfile).where(m.VoiceProfile.character_id == character_id)
        )
        row = result.scalars().first()
        if row is None:
            row = m.VoiceProfile(character_id=character_id)
            self._session.add(row)
            await self._session.flush()
        return _voice_profile(row)

    async def save(self, voice_profile: VoiceProfile) -> VoiceProfile:
        row = await self._session.get(m.VoiceProfile, voice_profile.id)
        if row is None:
            raise ValueError(f"voice profile {voice_profile.id} not found")
        row.provider = voice_profile.provider
        row.provider_voice_id = voice_profile.provider_voice_id
        row.language = voice_profile.language
        row.style = voice_profile.style
        row.pronunciation_dictionary = voice_profile.pronunciation_dictionary
        row.provenance = voice_profile.provenance.model_dump(mode="json")
        row.locked = voice_profile.locked
        row.version = voice_profile.version
        await self._session.flush()
        return _voice_profile(row)

    async def set_lock(self, character_id: str, locked: bool) -> VoiceProfile:
        result = await self._session.execute(
            select(m.VoiceProfile).where(m.VoiceProfile.character_id == character_id)
        )
        row = result.scalars().first()
        if row is None:
            raise ValueError(f"voice profile for character {character_id} not found")
        row.locked = locked
        await self._session.flush()
        return _voice_profile(row)

    async def unlock_and_bump_version(self, character_id: str) -> VoiceProfile:
        result = await self._session.execute(
            select(m.VoiceProfile).where(m.VoiceProfile.character_id == character_id)
        )
        row = result.scalars().first()
        if row is None:
            raise ValueError(f"voice profile for character {character_id} not found")
        row.locked = False
        row.version += 1
        await self._session.flush()
        return _voice_profile(row)


def _audio_production(row: m.ShotAudioProduction) -> ShotAudioProduction:
    return ShotAudioProduction(
        id=row.id,
        episode_id=row.episode_id,
        scene_number=row.scene_number,
        shot_number=row.shot_number,
        audio_mode=AudioMode(row.audio_mode),
        status=row.status,
        approved_take_asset_id=row.approved_take_asset_id,
        auto_retake_attempts=row.auto_retake_attempts,
        escalated=row.escalated,
    )


class SQLAlchemyAudioProductionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(
        self,
        episode_id: str,
        scene_number: int,
        shot_number: int,
        audio_mode: AudioMode = AudioMode.NATIVE,
    ) -> ShotAudioProduction:
        result = await self._session.execute(
            select(m.ShotAudioProduction).where(
                m.ShotAudioProduction.episode_id == episode_id,
                m.ShotAudioProduction.scene_number == scene_number,
                m.ShotAudioProduction.shot_number == shot_number,
            )
        )
        row = result.scalars().first()
        if row is None:
            row = m.ShotAudioProduction(
                episode_id=episode_id,
                scene_number=scene_number,
                shot_number=shot_number,
                audio_mode=audio_mode.value,
            )
            self._session.add(row)
            await self._session.flush()
        return _audio_production(row)

    async def get(self, production_id: str) -> ShotAudioProduction | None:
        row = await self._session.get(m.ShotAudioProduction, production_id)
        return _audio_production(row) if row is not None else None

    async def approve(self, production_id: str, asset_id: str) -> ShotAudioProduction:
        row = await self._session.get(m.ShotAudioProduction, production_id)
        if row is None:
            raise ValueError(f"audio production {production_id} not found")
        row.status = "approved"
        row.approved_take_asset_id = asset_id
        await self._session.flush()
        return _audio_production(row)

    async def list_by_episode(self, episode_id: str) -> list[ShotAudioProduction]:
        result = await self._session.execute(
            select(m.ShotAudioProduction).where(m.ShotAudioProduction.episode_id == episode_id)
        )
        return [_audio_production(row) for row in result.scalars()]

    async def record_retake_attempt(
        self, production_id: str, escalated: bool = False
    ) -> ShotAudioProduction:
        row = await self._session.get(m.ShotAudioProduction, production_id)
        if row is None:
            raise ValueError(f"audio production {production_id} not found")
        row.auto_retake_attempts += 1
        if escalated:
            row.escalated = True
        await self._session.flush()
        return _audio_production(row)


def _music_cue(row: m.MusicCue) -> MusicCue:
    return MusicCue(
        id=row.id,
        episode_id=row.episode_id,
        scene_number=row.scene_number,
        purpose=row.purpose,
        mood=row.mood,
        start_seconds=row.start_seconds,
        end_seconds=row.end_seconds,
        ducking_db=row.ducking_db,
        asset_id=row.asset_id,
        rights=RightsMetadata.model_validate(row.rights) if row.rights else RightsMetadata(),
        status=row.status,
    )


class SQLAlchemyMusicCueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        episode_id: str,
        purpose: str,
        mood: str,
        start_seconds: float,
        end_seconds: float,
        ducking_db: float = 0.0,
        scene_number: int | None = None,
    ) -> MusicCue:
        row = m.MusicCue(
            episode_id=episode_id,
            scene_number=scene_number,
            purpose=purpose,
            mood=mood,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            ducking_db=ducking_db,
        )
        self._session.add(row)
        await self._session.flush()
        return _music_cue(row)

    async def get(self, cue_id: str) -> MusicCue | None:
        row = await self._session.get(m.MusicCue, cue_id)
        return _music_cue(row) if row is not None else None

    async def update(self, cue: MusicCue) -> MusicCue:
        row = await self._session.get(m.MusicCue, cue.id)
        if row is None:
            raise ValueError(f"music cue {cue.id} not found")
        row.scene_number = cue.scene_number
        row.purpose = cue.purpose
        row.mood = cue.mood
        row.start_seconds = cue.start_seconds
        row.end_seconds = cue.end_seconds
        row.ducking_db = cue.ducking_db
        row.asset_id = cue.asset_id
        row.rights = cue.rights.model_dump(mode="json")
        row.status = cue.status
        await self._session.flush()
        return _music_cue(row)

    async def delete(self, cue_id: str) -> None:
        row = await self._session.get(m.MusicCue, cue_id)
        if row is not None:
            await self._session.delete(row)
            await self._session.flush()

    async def list_by_episode(self, episode_id: str) -> list[MusicCue]:
        result = await self._session.execute(
            select(m.MusicCue).where(m.MusicCue.episode_id == episode_id).order_by(m.MusicCue.start_seconds)
        )
        return [_music_cue(row) for row in result.scalars()]


def _sound_effect_cue(row: m.SoundEffectCue) -> SoundEffectCue:
    return SoundEffectCue(
        id=row.id,
        episode_id=row.episode_id,
        scene_number=row.scene_number,
        shot_number=row.shot_number,
        description=row.description,
        start_seconds=row.start_seconds,
        end_seconds=row.end_seconds,
        gain_db=row.gain_db,
        asset_id=row.asset_id,
        rights=RightsMetadata.model_validate(row.rights) if row.rights else RightsMetadata(),
        status=row.status,
    )


class SQLAlchemySoundEffectCueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        episode_id: str,
        scene_number: int,
        description: str,
        start_seconds: float,
        end_seconds: float,
        shot_number: int | None = None,
        gain_db: float = 0.0,
    ) -> SoundEffectCue:
        row = m.SoundEffectCue(
            episode_id=episode_id,
            scene_number=scene_number,
            shot_number=shot_number,
            description=description,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            gain_db=gain_db,
        )
        self._session.add(row)
        await self._session.flush()
        return _sound_effect_cue(row)

    async def get(self, cue_id: str) -> SoundEffectCue | None:
        row = await self._session.get(m.SoundEffectCue, cue_id)
        return _sound_effect_cue(row) if row is not None else None

    async def update(self, cue: SoundEffectCue) -> SoundEffectCue:
        row = await self._session.get(m.SoundEffectCue, cue.id)
        if row is None:
            raise ValueError(f"sound effect cue {cue.id} not found")
        row.scene_number = cue.scene_number
        row.shot_number = cue.shot_number
        row.description = cue.description
        row.start_seconds = cue.start_seconds
        row.end_seconds = cue.end_seconds
        row.gain_db = cue.gain_db
        row.asset_id = cue.asset_id
        row.rights = cue.rights.model_dump(mode="json")
        row.status = cue.status
        await self._session.flush()
        return _sound_effect_cue(row)

    async def delete(self, cue_id: str) -> None:
        row = await self._session.get(m.SoundEffectCue, cue_id)
        if row is not None:
            await self._session.delete(row)
            await self._session.flush()

    async def list_by_episode(self, episode_id: str) -> list[SoundEffectCue]:
        result = await self._session.execute(
            select(m.SoundEffectCue)
            .where(m.SoundEffectCue.episode_id == episode_id)
            .order_by(m.SoundEffectCue.start_seconds)
        )
        return [_sound_effect_cue(row) for row in result.scalars()]


def _subtitle_cue(row: m.SubtitleCue) -> SubtitleCue:
    return SubtitleCue(
        id=row.id,
        episode_id=row.episode_id,
        scene_number=row.scene_number,
        shot_number=row.shot_number,
        character_id=row.character_id,
        language=row.language,
        text=row.text,
        lines=row.lines,
        start_seconds=row.start_seconds,
        end_seconds=row.end_seconds,
    )


class SQLAlchemySubtitleCueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_track(
        self, episode_id: str, language: str, cues: list[dict]
    ) -> list[SubtitleCue]:
        await self._session.execute(
            delete(m.SubtitleCue).where(
                m.SubtitleCue.episode_id == episode_id, m.SubtitleCue.language == language
            )
        )
        rows = [
            m.SubtitleCue(
                episode_id=episode_id,
                scene_number=cue["scene_number"],
                shot_number=cue["shot_number"],
                character_id=cue.get("character_id"),
                language=language,
                text=cue["text"],
                lines=cue["lines"],
                start_seconds=cue["start_seconds"],
                end_seconds=cue["end_seconds"],
            )
            for cue in cues
        ]
        self._session.add_all(rows)
        await self._session.flush()
        return [_subtitle_cue(row) for row in rows]

    async def get(self, cue_id: str) -> SubtitleCue | None:
        row = await self._session.get(m.SubtitleCue, cue_id)
        return _subtitle_cue(row) if row is not None else None

    async def list_by_episode(self, episode_id: str, language: str = "en") -> list[SubtitleCue]:
        result = await self._session.execute(
            select(m.SubtitleCue)
            .where(m.SubtitleCue.episode_id == episode_id, m.SubtitleCue.language == language)
            .order_by(m.SubtitleCue.start_seconds)
        )
        return [_subtitle_cue(row) for row in result.scalars()]


def _media_qc_attempt(row: m.MediaQCAttempt) -> MediaQCAttempt:
    return MediaQCAttempt(
        id=row.id,
        asset_id=row.asset_id,
        dimension=MediaQCDimension(row.dimension),
        status=QCStatus(row.status),
        score=row.score,
        evidence=row.evidence,
        reasons=row.reasons,
        repair_recommendation=row.repair_recommendation,
        created_at=row.created_at,
    )


class SQLAlchemyMediaQCRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        asset_id: str,
        dimension: MediaQCDimension,
        status: QCStatus,
        score: float,
        evidence: dict,
        reasons: list[str],
        repair_recommendation: str = "",
    ) -> MediaQCAttempt:
        row = m.MediaQCAttempt(
            asset_id=asset_id,
            dimension=dimension.value,
            status=status.value,
            score=score,
            evidence=evidence,
            reasons=reasons,
            repair_recommendation=repair_recommendation,
        )
        self._session.add(row)
        await self._session.flush()
        return _media_qc_attempt(row)

    async def list_by_asset(self, asset_id: str) -> list[MediaQCAttempt]:
        result = await self._session.execute(
            select(m.MediaQCAttempt)
            .where(m.MediaQCAttempt.asset_id == asset_id)
            .order_by(m.MediaQCAttempt.created_at)
        )
        return [_media_qc_attempt(row) for row in result.scalars()]

    async def get_latest(self, asset_id: str, dimension: MediaQCDimension) -> MediaQCAttempt | None:
        result = await self._session.execute(
            select(m.MediaQCAttempt)
            .where(
                m.MediaQCAttempt.asset_id == asset_id,
                m.MediaQCAttempt.dimension == dimension.value,
            )
            .order_by(m.MediaQCAttempt.created_at.desc())
            .limit(1)
        )
        row = result.scalars().first()
        return _media_qc_attempt(row) if row is not None else None

    async def list_by_assets(self, asset_ids: list[str]) -> list[MediaQCAttempt]:
        if not asset_ids:
            return []
        result = await self._session.execute(
            select(m.MediaQCAttempt).where(m.MediaQCAttempt.asset_id.in_(asset_ids))
        )
        return [_media_qc_attempt(row) for row in result.scalars()]


def _episode_render(row: m.EpisodeRender) -> EpisodeRender:
    return EpisodeRender(
        id=row.id,
        episode_id=row.episode_id,
        version=row.version,
        status=row.status,
        render_asset_id=row.render_asset_id,
        parent_render_id=row.parent_render_id,
        source_script_version=row.source_script_version,
        input_asset_ids=row.input_asset_ids,
        created_at=row.created_at,
    )


class SQLAlchemyEpisodeRenderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        episode_id: str,
        render_asset_id: str,
        source_script_version: int,
        input_asset_ids: list[str],
        parent_render_id: str | None = None,
    ) -> EpisodeRender:
        result = await self._session.execute(
            select(m.EpisodeRender).where(m.EpisodeRender.episode_id == episode_id)
        )
        existing = result.scalars().all()
        version = max((row.version for row in existing), default=0) + 1
        row = m.EpisodeRender(
            episode_id=episode_id,
            version=version,
            render_asset_id=render_asset_id,
            parent_render_id=parent_render_id,
            source_script_version=source_script_version,
            input_asset_ids=input_asset_ids,
        )
        self._session.add(row)
        await self._session.flush()
        return _episode_render(row)

    async def get(self, render_id: str) -> EpisodeRender | None:
        row = await self._session.get(m.EpisodeRender, render_id)
        return _episode_render(row) if row is not None else None

    async def list_by_episode(self, episode_id: str) -> list[EpisodeRender]:
        result = await self._session.execute(
            select(m.EpisodeRender)
            .where(m.EpisodeRender.episode_id == episode_id)
            .order_by(m.EpisodeRender.version)
        )
        return [_episode_render(row) for row in result.scalars()]

    async def approve(self, render_id: str) -> EpisodeRender:
        row = await self._session.get(m.EpisodeRender, render_id)
        if row is None:
            raise ValueError(f"episode render {render_id} not found")
        result = await self._session.execute(
            select(m.EpisodeRender).where(
                m.EpisodeRender.episode_id == row.episode_id,
                m.EpisodeRender.status == "approved",
                m.EpisodeRender.id != render_id,
            )
        )
        for other in result.scalars():
            other.status = "superseded"
        row.status = "approved"
        await self._session.flush()
        return _episode_render(row)

    async def get_current(self, episode_id: str) -> EpisodeRender | None:
        result = await self._session.execute(
            select(m.EpisodeRender).where(
                m.EpisodeRender.episode_id == episode_id, m.EpisodeRender.status == "approved"
            )
        )
        row = result.scalars().first()
        return _episode_render(row) if row is not None else None


def _cost_record(row: m.CostRecord) -> CostRecord:
    return CostRecord(
        id=row.id,
        provider=row.provider,
        model=row.model,
        stage=row.stage,
        project_id=row.project_id,
        series_id=row.series_id,
        episode_id=row.episode_id,
        scene_number=row.scene_number,
        shot_number=row.shot_number,
        attempt=row.attempt,
        quantity=row.quantity,
        unit=row.unit,
        cost_usd=row.cost_usd,
        cost_known=row.cost_known,
        latency_ms=row.latency_ms,
        asset_id=row.asset_id,
        failure_reason=row.failure_reason,
        created_at=row.created_at,
    )


class SQLAlchemyCostRecordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        provider: str,
        model: str,
        stage: str,
        project_id: str | None = None,
        series_id: str | None = None,
        episode_id: str | None = None,
        scene_number: int | None = None,
        shot_number: int | None = None,
        attempt: int = 1,
        quantity: float = 0.0,
        unit: str = "",
        cost_usd: float | None = None,
        cost_known: bool = False,
        latency_ms: float | None = None,
        asset_id: str | None = None,
        failure_reason: str = "",
    ) -> CostRecord:
        row = m.CostRecord(
            provider=provider,
            model=model,
            stage=stage,
            project_id=project_id,
            series_id=series_id,
            episode_id=episode_id,
            scene_number=scene_number,
            shot_number=shot_number,
            attempt=attempt,
            quantity=quantity,
            unit=unit,
            cost_usd=cost_usd,
            cost_known=cost_known,
            latency_ms=latency_ms,
            asset_id=asset_id,
            failure_reason=failure_reason,
        )
        self._session.add(row)
        await self._session.flush()
        return _cost_record(row)

    async def list_by_project(self, project_id: str) -> list[CostRecord]:
        result = await self._session.execute(
            select(m.CostRecord)
            .where(m.CostRecord.project_id == project_id)
            .order_by(m.CostRecord.created_at)
        )
        return [_cost_record(row) for row in result.scalars()]

    async def list_by_episode(self, episode_id: str) -> list[CostRecord]:
        result = await self._session.execute(
            select(m.CostRecord)
            .where(m.CostRecord.episode_id == episode_id)
            .order_by(m.CostRecord.created_at)
        )
        return [_cost_record(row) for row in result.scalars()]


def _episode_metric(row: m.EpisodeMetric) -> EpisodeMetric:
    return EpisodeMetric(
        id=row.id,
        episode_id=row.episode_id,
        render_version=row.render_version,
        source=row.source,
        observation_window_start=row.observation_window_start,
        observation_window_end=row.observation_window_end,
        impressions=row.impressions,
        views=row.views,
        avg_watch_seconds=row.avg_watch_seconds,
        completion_rate=row.completion_rate,
        three_second_retention_rate=row.three_second_retention_rate,
        rewatch_rate=row.rewatch_rate,
        continuation_rate=row.continuation_rate,
        engagement=row.engagement,
        raw_payload=row.raw_payload,
        imported_at=row.imported_at,
    )


class SQLAlchemyMetricsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        episode_id: str,
        render_version: int,
        source: str,
        observation_window_start: datetime,
        observation_window_end: datetime,
        raw_payload: dict,
        impressions: int | None = None,
        views: int | None = None,
        avg_watch_seconds: float | None = None,
        completion_rate: float | None = None,
        three_second_retention_rate: float | None = None,
        rewatch_rate: float | None = None,
        continuation_rate: float | None = None,
        engagement: dict | None = None,
    ) -> EpisodeMetric:
        result = await self._session.execute(
            select(m.EpisodeMetric).where(
                m.EpisodeMetric.episode_id == episode_id,
                m.EpisodeMetric.render_version == render_version,
                m.EpisodeMetric.source == source,
                m.EpisodeMetric.observation_window_start == observation_window_start,
                m.EpisodeMetric.observation_window_end == observation_window_end,
            )
        )
        row = result.scalars().first()
        if row is None:
            row = m.EpisodeMetric(
                episode_id=episode_id,
                render_version=render_version,
                source=source,
                observation_window_start=observation_window_start,
                observation_window_end=observation_window_end,
            )
            self._session.add(row)
        row.impressions = impressions
        row.views = views
        row.avg_watch_seconds = avg_watch_seconds
        row.completion_rate = completion_rate
        row.three_second_retention_rate = three_second_retention_rate
        row.rewatch_rate = rewatch_rate
        row.continuation_rate = continuation_rate
        row.engagement = engagement or {}
        row.raw_payload = raw_payload
        await self._session.flush()
        return _episode_metric(row)

    async def list_by_episode(self, episode_id: str) -> list[EpisodeMetric]:
        result = await self._session.execute(
            select(m.EpisodeMetric)
            .where(m.EpisodeMetric.episode_id == episode_id)
            .order_by(m.EpisodeMetric.observation_window_start)
        )
        return [_episode_metric(row) for row in result.scalars()]


def _human_feedback(row: m.HumanFeedback) -> HumanFeedback:
    return HumanFeedback(
        id=row.id,
        asset_id=row.asset_id,
        project_id=row.project_id,
        decision=row.decision,
        reason=row.reason,
        rating=row.rating,
        tags=row.tags,
        reviewer=row.reviewer,
        provider=row.provider,
        model=row.model,
        created_at=row.created_at,
    )


class SQLAlchemyHumanFeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        asset_id: str,
        decision: str,
        project_id: str | None = None,
        reason: str = "",
        rating: int | None = None,
        tags: list[str] | None = None,
        reviewer: str = "",
        provider: str = "",
        model: str = "",
    ) -> HumanFeedback:
        row = m.HumanFeedback(
            asset_id=asset_id,
            decision=decision,
            project_id=project_id,
            reason=reason,
            rating=rating,
            tags=tags or [],
            reviewer=reviewer,
            provider=provider,
            model=model,
        )
        self._session.add(row)
        await self._session.flush()
        return _human_feedback(row)

    async def list_by_asset(self, asset_id: str) -> list[HumanFeedback]:
        result = await self._session.execute(
            select(m.HumanFeedback)
            .where(m.HumanFeedback.asset_id == asset_id)
            .order_by(m.HumanFeedback.created_at)
        )
        return [_human_feedback(row) for row in result.scalars()]

    async def list_by_project(self, project_id: str) -> list[HumanFeedback]:
        result = await self._session.execute(
            select(m.HumanFeedback)
            .where(m.HumanFeedback.project_id == project_id)
            .order_by(m.HumanFeedback.created_at)
        )
        return [_human_feedback(row) for row in result.scalars()]
