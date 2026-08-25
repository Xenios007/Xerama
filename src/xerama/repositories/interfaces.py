"""Repository Protocols and infra DTOs.

Pipeline/service code type-hints against these Protocols. `SQLAlchemyProjectRepository`
et al. in `sqlalchemy_impl.py` are the only implementation today; a future
Postgres-backed or in-memory-fake implementation can be substituted without
touching pipeline code.
"""

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field

from xerama.domain.asset import Asset, AssetOwnership, AssetProvenance, AssetStatus, AssetType
from xerama.domain.audio_production import ShotAudioProduction
from xerama.domain.brief import CreativeBrief
from xerama.domain.canon import CanonEvent
from xerama.domain.character import Character, CharacterCast, PhysicalStateVariant, WardrobeVariant
from xerama.domain.episode import EpisodeOutline, EpisodeScript
from xerama.domain.analytics import EpisodeMetric
from xerama.domain.auth import AuthSession, ProjectMembership, User
from xerama.domain.cost import CostRecord
from xerama.domain.episode_render import EpisodeRender
from xerama.domain.eval import EvalRunResult
from xerama.domain.feedback import HumanFeedback
from xerama.domain.media_qc import MediaQCAttempt
from xerama.domain.music import MusicCue
from xerama.domain.quality import QCResult
from xerama.domain.scene import EpisodeShotPlan
from xerama.domain.season import SeasonPlan
from xerama.domain.sound_effect import SoundEffectCue
from xerama.domain.storyboard import Storyboard
from xerama.domain.subtitle import SubtitleCue
from xerama.domain.story import ConceptCandidate, JudgeResult
from xerama.domain.style_bible import StyleBible
from xerama.domain.video_production import ShotVideoProduction
from xerama.domain.voice import VoiceProfile
from xerama.domain.enums import JobStage, JobStatus, AudioMode, MediaQCDimension, ProjectRole, QCStatus


class ProjectRecord(BaseModel):
    id: str
    name: str
    description: str = ""
    status: str = "active"
    created_at: datetime


class SeriesRecord(BaseModel):
    id: str
    project_id: str
    title: str
    logline: str = ""
    genre: list[str] = Field(default_factory=list)
    target_audience: str = "general"
    episode_count_target: int = 3
    episode_duration_target_seconds: int = 75
    status: str = "draft"


class EpisodeRecord(BaseModel):
    id: str
    series_id: str
    episode_number: int
    status: str
    version: int = 1
    outline: EpisodeOutline
    script: EpisodeScript | None = None


class SeasonPlanRecord(BaseModel):
    id: str
    series_id: str
    version: int
    status: str = "draft"
    plan: SeasonPlan
    qc_status: str = "pass"
    qc_score: float = 0.0
    qc_reasons: list[str] = Field(default_factory=list)


class JobRecord(BaseModel):
    id: str
    project_id: str
    stage: JobStage
    status: JobStatus
    provider: str = ""
    model: str = ""
    attempt: int = 1
    error: str = ""
    # Job-queue fields (MODULE-041) - unused by the existing synchronous
    # JobRunner path, only by enqueue/claim/heartbeat.
    priority: int = 0
    payload: dict = Field(default_factory=dict)
    depends_on_job_id: str | None = None
    max_attempts: int = 3
    lease_owner: str | None = None
    result_asset_ids: list[str] = Field(default_factory=list)
    # MODULE-050 - already existed on the DB row, just never surfaced in
    # the domain model until observability needed to compute durations.
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ProjectRepository(Protocol):
    async def create(self, name: str, description: str = "") -> ProjectRecord: ...
    async def get(self, project_id: str) -> ProjectRecord | None: ...

    async def list_all(self) -> list[ProjectRecord]:
        """See MODULE-051 - every project, newest first."""
        ...

    async def update(
        self, project_id: str, name: str | None = None, description: str | None = None
    ) -> ProjectRecord:
        """Raises `ValueError` if the project doesn't exist, or
        `PermissionError` if it's archived - "validate edits against
        locked/published state"."""
        ...

    async def archive(self, project_id: str) -> ProjectRecord:
        """Idempotent - archiving an already-archived project is a no-op,
        not an error."""
        ...


class ConceptRepository(Protocol):
    """Persists both dual-generation candidates and the judge decision. Never
    deletes a rejected candidate - see ADR-019."""

    async def save_candidate(
        self,
        project_id: str,
        batch_id: str,
        slot: str,
        provider: str,
        model: str,
        brief: CreativeBrief,
        candidate: ConceptCandidate,
    ) -> str: ...

    async def save_judge_decision(
        self,
        project_id: str,
        batch_id: str,
        provider: str,
        model: str,
        result: JudgeResult,
        approved_concept: ConceptCandidate,
    ) -> str: ...

    async def list_candidates(self, project_id: str) -> list["ConceptCandidateRecord"]:
        """See MODULE-057 - "inspect candidate lineage and scores." Every
        candidate ever generated for this project, accepted or not
        (ADR-019 - never deleted on rejection)."""
        ...

    async def list_judge_decisions(self, project_id: str) -> list["JudgeDecisionRecord"]:
        ...


class ConceptCandidateRecord(BaseModel):
    id: str
    project_id: str
    batch_id: str
    slot: str
    provider: str
    model: str
    candidate: ConceptCandidate
    accepted: bool
    created_at: datetime


class JudgeDecisionRecord(BaseModel):
    id: str
    project_id: str
    batch_id: str
    decision: str
    provider: str
    model: str
    result: JudgeResult
    approved_concept: ConceptCandidate
    created_at: datetime


class SeriesRepository(Protocol):
    async def create_series(
        self, project_id: str, brief: CreativeBrief, approved_concept: ConceptCandidate
    ) -> SeriesRecord: ...

    async def get_series(self, series_id: str) -> SeriesRecord | None: ...

    async def save_bible(self, series_id: str, bible) -> None: ...

    async def get_bible(self, series_id: str): ...

    async def save_cast(self, series_id: str, cast: CharacterCast) -> None: ...

    async def get_cast(self, series_id: str) -> CharacterCast: ...

    async def list_by_project(self, project_id: str) -> list[SeriesRecord]:
        """See MODULE-051 - every series ever created for this project."""
        ...


class SeasonRepository(Protocol):
    """Versioned season/reveal plans - see Module 01 and ADR-019 (never
    overwrite a rejected/superseded generation)."""

    async def create_plan(
        self, series_id: str, plan: SeasonPlan, qc: QCResult
    ) -> SeasonPlanRecord: ...

    async def get_current_plan(self, series_id: str) -> SeasonPlanRecord | None:
        """Latest APPROVED version if one exists, else the latest version overall."""
        ...

    async def get_version(self, series_id: str, version: int) -> SeasonPlanRecord | None: ...

    async def list_versions(self, series_id: str) -> list[SeasonPlanRecord]: ...

    async def approve_version(self, series_id: str, version: int) -> SeasonPlanRecord: ...


class EpisodeRepository(Protocol):
    async def save_outline(self, series_id: str, outline: EpisodeOutline) -> EpisodeRecord: ...

    async def save_script(self, episode_id: str, script: EpisodeScript) -> None: ...

    async def save_shot_plan(self, episode_id: str, plan: EpisodeShotPlan) -> None: ...

    async def get_shot_plan(self, episode_id: str) -> EpisodeShotPlan | None: ...

    async def save_quality_report(self, episode_id: str, result: QCResult) -> None: ...

    async def list_quality_reports(self, episode_id: str) -> list[QCResult]:
        """See MODULE-057 - "show continuity/quality gates" for an
        episode without re-running generation. Every QC attempt ever
        recorded for this episode (director/retention/continuity),
        oldest first."""
        ...

    async def save_canon_event(self, episode_id: str, event: CanonEvent) -> None: ...

    async def invalidate_canon_events(self, episode_id: str) -> None:
        """Soft-retires this episode's previously committed canon events
        (sets `committed=False`) without deleting them - called before a
        regeneration re-commits fresh events, so `list_canon_events` never
        double-counts a superseded take. See ADR-019 / Module 02
        "regeneration without corrupting later canon"."""
        ...

    async def list_canon_events(
        self, series_id: str, before_episode: int | None = None
    ) -> list[CanonEvent]:
        """Committed canon events for a series, optionally only those from
        episodes strictly before `before_episode` - the bounded context a
        later episode's generation is allowed to see."""
        ...

    async def set_status(self, episode_id: str, status: str) -> None: ...

    async def list_by_series(self, series_id: str) -> list[EpisodeRecord]: ...

    async def get(self, episode_id: str) -> EpisodeRecord | None: ...

    async def get_by_number(self, series_id: str, episode_number: int) -> EpisodeRecord | None: ...


class JobRepository(Protocol):
    """Persistent generation jobs - see docs/ARCHITECTURE.md section 11, ADR-023."""

    async def create(self, project_id: str, stage: JobStage) -> JobRecord: ...

    async def start(self, job_id: str, provider: str = "", model: str = "") -> None: ...

    async def succeed(self, job_id: str) -> None: ...

    async def fail(self, job_id: str, error: str) -> None: ...

    async def get(self, job_id: str) -> JobRecord | None: ...

    async def list_by_project(self, project_id: str) -> list[JobRecord]:
        """See MODULE-050 - every job (both the synchronous JobRunner path
        and the MODULE-041 queue path) ever created for this project,
        newest first."""
        ...

    async def list_filtered(
        self,
        project_id: str | None = None,
        stage: JobStage | None = None,
        status: JobStatus | None = None,
    ) -> list[JobRecord]:
        """See MODULE-054 - the general job-progress query the UI polls;
        any combination of filters, newest first."""
        ...

    # --- Job-queue methods (MODULE-041) - additive, coexist with the
    # synchronous create/start/succeed/fail path above used by JobRunner.
    # Nothing here changes existing behavior for existing call sites.

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
    ) -> JobRecord: ...

    async def claim(self, worker_id: str, lease_seconds: int = 60) -> JobRecord | None:
        """Atomically selects and claims the highest-priority, oldest,
        currently-eligible queued job (dependency satisfied, `scheduled_at`
        due) and moves it to `running`. Returns `None` if nothing is
        eligible. Safe against two workers racing for the same job."""
        ...

    async def heartbeat(self, job_id: str, worker_id: str, lease_seconds: int = 60) -> None: ...

    async def succeed_job(self, job_id: str, result_asset_ids: list[str] | None = None) -> JobRecord: ...

    async def fail_job_attempt(self, job_id: str, error: str, retriable: bool) -> JobRecord:
        """Retriable + attempts remaining -> requeues with exponential
        backoff. Otherwise -> terminal `failed` (dead-letter) with `error`
        as the operator-visible reason."""
        ...

    async def cancel(self, job_id: str) -> JobRecord: ...

    async def recover_abandoned(self, now: datetime | None = None) -> list[JobRecord]:
        """Requeues every `running` job whose lease has expired - "recover
        abandoned running jobs after restart"."""
        ...

    async def list_queued(self, stage: JobStage | None = None) -> list[JobRecord]: ...

    async def list_failed(self, project_id: str | None = None) -> list[JobRecord]: ...


class AssetRepository(Protocol):
    """Persistent media assets - see Module 04, ADR-020/022."""

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
    ) -> Asset: ...

    async def get(self, asset_id: str) -> Asset | None: ...

    async def get_by_hash(self, content_hash: str) -> Asset | None: ...

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
        """`status` filter added for MODULE-060 - "queue awaiting-review
        items" (`status=pending`) without pulling every asset for a
        project and filtering client-side."""
        ...

    async def list_all(self) -> list[Asset]:
        """Every asset row - used for orphan/integrity scans."""
        ...

    async def set_status(
        self, asset_id: str, status: AssetStatus, rejection_reason: str = ""
    ) -> Asset: ...

    async def delete(self, asset_id: str) -> None: ...


class CharacterCastingRepository(Protocol):
    """Single-character identity CRUD/lock/version + wardrobe/physical-state
    variants - see Module 05. Distinct from `SeriesRepository.save_cast`/
    `get_cast`, which handle the whole-cast bulk generation output."""

    async def get_character(self, character_id: str) -> Character | None: ...

    async def get_character_series_id(self, character_id: str) -> str | None:
        """See MODULE-067 - authorization needs to resolve character ->
        series -> project without pulling (and paying the cost of
        rebuilding) the full `Character` domain object."""
        ...

    async def save_character(self, character: Character) -> Character:
        """Persists every field of `character` over the existing row.
        Raises `ValueError` if the character does not already exist."""
        ...

    async def set_lock(self, character_id: str, locked: bool) -> Character: ...

    async def unlock_and_bump_version(self, character_id: str) -> Character:
        """Explicit deliberate recast: unlocks and increments `version`."""
        ...

    async def create_wardrobe_variant(
        self,
        character_id: str,
        label: str,
        reference_asset_ids: list[str],
        description: str = "",
    ) -> WardrobeVariant: ...

    async def list_wardrobe_variants(self, character_id: str) -> list[WardrobeVariant]: ...

    async def create_physical_state_variant(
        self,
        character_id: str,
        label: str,
        reference_asset_ids: list[str],
        description: str = "",
    ) -> PhysicalStateVariant: ...

    async def list_physical_state_variants(self, character_id: str) -> list[PhysicalStateVariant]: ...


class StyleBibleRepository(Protocol):
    """One production-anchor row per series - see Module 06, ADR-013."""

    async def get_or_create(self, series_id: str) -> StyleBible: ...

    async def save(self, style_bible: StyleBible) -> StyleBible:
        """Persists every field over the existing row. Raises `ValueError`
        if the style bible does not already exist."""
        ...

    async def set_lock(self, series_id: str, locked: bool) -> StyleBible: ...

    async def unlock_and_bump_version(self, series_id: str) -> StyleBible: ...


class StoryboardRepository(Protocol):
    """Per-shot still-image workflow records - see Module 06."""

    async def get_or_create(
        self, episode_id: str, scene_number: int, shot_number: int, layout_description: str = ""
    ) -> Storyboard: ...

    async def get(self, storyboard_id: str) -> Storyboard | None: ...

    async def approve(self, storyboard_id: str, asset_id: str) -> Storyboard: ...

    async def list_by_episode(self, episode_id: str) -> list[Storyboard]: ...

    async def record_retake_attempt(self, storyboard_id: str, escalated: bool = False) -> Storyboard:
        """See MODULE-045 - increments `auto_retake_attempts` (never
        reset) and sets `escalated` once the repair budget is exhausted."""
        ...


class VideoProductionRepository(Protocol):
    """Per-shot video workflow records - see Module 08."""

    async def get_or_create(
        self,
        episode_id: str,
        scene_number: int,
        shot_number: int,
        continuity_group: str | None = None,
    ) -> ShotVideoProduction: ...

    async def get(self, production_id: str) -> ShotVideoProduction | None: ...

    async def get_previous_in_continuity_group(
        self, episode_id: str, continuity_group: str, before_scene_number: int, before_shot_number: int
    ) -> ShotVideoProduction | None:
        """The production record with the highest (scene_number, shot_number)
        strictly before the given position, sharing `continuity_group` -
        i.e. the immediately preceding shot in the same continuity chain."""
        ...

    async def approve(self, production_id: str, asset_id: str) -> ShotVideoProduction: ...

    async def set_extracted_last_frame(self, production_id: str, asset_id: str) -> ShotVideoProduction: ...

    async def list_by_episode(self, episode_id: str) -> list[ShotVideoProduction]: ...

    async def record_retake_attempt(
        self, production_id: str, escalated: bool = False
    ) -> ShotVideoProduction:
        """See MODULE-045 - see `StoryboardRepository.record_retake_attempt`."""
        ...


class VoiceProfileRepository(Protocol):
    """One row per character - see MODULE-034."""

    async def get_or_create(self, character_id: str) -> VoiceProfile: ...

    async def save(self, voice_profile: VoiceProfile) -> VoiceProfile:
        """Persists every field over the existing row. Raises `ValueError`
        if the voice profile does not already exist."""
        ...

    async def set_lock(self, character_id: str, locked: bool) -> VoiceProfile: ...

    async def unlock_and_bump_version(self, character_id: str) -> VoiceProfile: ...


class AudioProductionRepository(Protocol):
    """Per-shot dialogue/audio workflow records - see MODULE-035."""

    async def get_or_create(
        self,
        episode_id: str,
        scene_number: int,
        shot_number: int,
        audio_mode: AudioMode = AudioMode.NATIVE,
    ) -> ShotAudioProduction: ...

    async def get(self, production_id: str) -> ShotAudioProduction | None: ...

    async def approve(self, production_id: str, asset_id: str) -> ShotAudioProduction: ...

    async def list_by_episode(self, episode_id: str) -> list[ShotAudioProduction]: ...

    async def record_retake_attempt(
        self, production_id: str, escalated: bool = False
    ) -> ShotAudioProduction:
        """See MODULE-045 - see `StoryboardRepository.record_retake_attempt`."""
        ...


class MusicCueRepository(Protocol):
    """See MODULE-037."""

    async def create(
        self,
        episode_id: str,
        purpose: str,
        mood: str,
        start_seconds: float,
        end_seconds: float,
        ducking_db: float = 0.0,
        scene_number: int | None = None,
    ) -> MusicCue: ...

    async def get(self, cue_id: str) -> MusicCue | None: ...

    async def update(self, cue: MusicCue) -> MusicCue:
        """Persists every field over the existing row. Raises `ValueError`
        if the cue does not already exist."""
        ...

    async def delete(self, cue_id: str) -> None: ...

    async def list_by_episode(self, episode_id: str) -> list[MusicCue]: ...


class SoundEffectCueRepository(Protocol):
    """See MODULE-038."""

    async def create(
        self,
        episode_id: str,
        scene_number: int,
        description: str,
        start_seconds: float,
        end_seconds: float,
        shot_number: int | None = None,
        gain_db: float = 0.0,
    ) -> SoundEffectCue: ...

    async def get(self, cue_id: str) -> SoundEffectCue | None: ...

    async def update(self, cue: SoundEffectCue) -> SoundEffectCue:
        """Persists every field over the existing row. Raises `ValueError`
        if the cue does not already exist."""
        ...

    async def delete(self, cue_id: str) -> None: ...

    async def list_by_episode(self, episode_id: str) -> list[SoundEffectCue]: ...


class SubtitleCueRepository(Protocol):
    """See MODULE-039. `replace_track` deletes every existing cue for
    (episode_id, language) and inserts the given ones atomically, so
    regeneration is idempotent rather than accumulating duplicates."""

    async def replace_track(
        self, episode_id: str, language: str, cues: list[dict]
    ) -> list[SubtitleCue]: ...

    async def get(self, cue_id: str) -> SubtitleCue | None: ...

    async def list_by_episode(self, episode_id: str, language: str = "en") -> list[SubtitleCue]: ...


class MediaQCRepository(Protocol):
    """See MODULE-044. Every call inserts a new row - a QC attempt is
    never overwritten (ADR-019)."""

    async def create(
        self,
        asset_id: str,
        dimension: MediaQCDimension,
        status: QCStatus,
        score: float,
        evidence: dict,
        reasons: list[str],
        repair_recommendation: str = "",
    ) -> MediaQCAttempt: ...

    async def list_by_asset(self, asset_id: str) -> list[MediaQCAttempt]: ...

    async def get_latest(
        self, asset_id: str, dimension: MediaQCDimension
    ) -> MediaQCAttempt | None: ...

    async def list_by_assets(self, asset_ids: list[str]) -> list[MediaQCAttempt]:
        """See MODULE-064 - one bulk `IN` query for provider ranking
        instead of N+1 per-asset lookups."""
        ...


class EpisodeRenderRepository(Protocol):
    """See MODULE-047. Every `create` call inserts a new, immutable
    version row - never overwritten or deleted."""

    async def create(
        self,
        episode_id: str,
        render_asset_id: str,
        source_script_version: int,
        input_asset_ids: list[str],
        parent_render_id: str | None = None,
    ) -> EpisodeRender: ...

    async def get(self, render_id: str) -> EpisodeRender | None: ...

    async def list_by_episode(self, episode_id: str) -> list[EpisodeRender]: ...

    async def approve(self, render_id: str) -> EpisodeRender:
        """Sets this render `approved` and every other render for the
        same episode currently `approved` to `superseded` - "current" is
        always exactly zero or one row per episode. Re-approving an older
        `superseded` row is how rollback works."""
        ...

    async def get_current(self, episode_id: str) -> EpisodeRender | None:
        """The single `approved` render for this episode, if any."""
        ...


class CostRecordRepository(Protocol):
    """See MODULE-049. Append-only - every call inserts a new row."""

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
    ) -> CostRecord: ...

    async def list_by_project(self, project_id: str) -> list[CostRecord]: ...

    async def list_by_episode(self, episode_id: str) -> list[CostRecord]: ...


class MetricsRepository(Protocol):
    """See MODULE-061. `upsert` is keyed on
    (episode_id, render_version, source, observation_window_start,
    observation_window_end) - re-importing the same window updates that
    row rather than accumulating duplicates ("deduplication")."""

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
    ) -> EpisodeMetric: ...

    async def list_by_episode(self, episode_id: str) -> list[EpisodeMetric]: ...


class HumanFeedbackRepository(Protocol):
    """See MODULE-065. Append-only."""

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
    ) -> HumanFeedback: ...

    async def list_by_asset(self, asset_id: str) -> list[HumanFeedback]: ...

    async def list_by_project(self, project_id: str) -> list[HumanFeedback]: ...


class EvalRunRepository(Protocol):
    """See MODULE-072. Append-only - every eval run is its own row,
    never overwritten, so a benchmark's history survives a later
    re-run."""

    async def create(
        self,
        case_id: str,
        role: str,
        dataset_version: str,
        provider: str,
        model: str,
        schema_valid: bool,
        quality_score: float | None = None,
        quality_reasons: list[str] | None = None,
        latency_ms: float | None = None,
        error: str = "",
        raw_response_excerpt: str = "",
    ) -> EvalRunResult: ...

    async def list_by_role(self, role: str) -> list[EvalRunResult]: ...

    async def list_all(self) -> list[EvalRunResult]: ...

    async def set_human_preference(self, run_id: str, preference: str) -> EvalRunResult: ...


class UserRepository(Protocol):
    """See MODULE-067. `email` is unique - `get_by_email` backs both
    registration's duplicate check and login."""

    async def create(self, email: str, password_hash: str, display_name: str = "") -> User: ...

    async def get(self, user_id: str) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...


class AuthSessionRepository(Protocol):
    """See MODULE-067. An opaque bearer token, not a JWT - validity is a
    DB lookup + expiry check, never signature verification."""

    async def create(self, user_id: str, token: str, expires_at: datetime) -> AuthSession: ...

    async def get_by_token(self, token: str) -> AuthSession | None: ...

    async def delete_by_token(self, token: str) -> None: ...


class ProjectMembershipRepository(Protocol):
    """See MODULE-067. One row per (project_id, user_id) - `grant`
    upserts the role if a membership already exists rather than creating
    a duplicate."""

    async def grant(self, project_id: str, user_id: str, role: ProjectRole) -> ProjectMembership: ...

    async def get(self, project_id: str, user_id: str) -> ProjectMembership | None: ...

    async def list_by_user(self, user_id: str) -> list[ProjectMembership]: ...

    async def list_by_project(self, project_id: str) -> list[ProjectMembership]: ...

    async def revoke(self, project_id: str, user_id: str) -> None: ...
