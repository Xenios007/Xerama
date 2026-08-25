"""ORM models mirroring docs/DATA_MODEL.md.

Nested/flexible structures (lists, scored dicts, DNA, camera/visual specs)
are stored as JSON columns rather than fully normalized tables - this keeps
V1 small while the repository layer still gives us a clean seam for a
future PostgreSQL migration (ADR-021). Relational fields that matter for
querying/joins (foreign keys, episode/scene/shot numbers, status) stay as
real columns.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from xerama.db.base import Base, utcnow


def _id() -> str:
    return uuid.uuid4().hex


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="active")
    default_language: Mapped[str] = mapped_column(String(16), default="en")
    target_platform: Mapped[str] = mapped_column(String(64), default="vertical_microdrama")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    series: Mapped[list["Series"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    jobs: Mapped[list["GenerationJob"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    concept_candidates: Mapped[list["ConceptCandidateRecord"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    judge_decisions: Mapped[list["JudgeDecisionRecord"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ConceptCandidateRecord(Base):
    """Both candidates from Standard-mode dual generation. Never deleted on
    rejection - see ADR-019 / docs/ARCHITECTURE.md section 4."""

    __tablename__ = "concept_candidates"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    batch_id: Mapped[str] = mapped_column(String(32), index=True)
    slot: Mapped[str] = mapped_column(String(1))  # "A" or "B"
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    brief: Mapped[dict] = mapped_column(JSON)
    candidate: Mapped[dict] = mapped_column(JSON)
    accepted: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="concept_candidates")


class JudgeDecisionRecord(Base):
    __tablename__ = "judge_decisions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    batch_id: Mapped[str] = mapped_column(String(32), index=True)
    decision: Mapped[str] = mapped_column(String(8))
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    result: Mapped[dict] = mapped_column(JSON)
    approved_concept: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="judge_decisions")


class Series(Base):
    __tablename__ = "series"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(255))
    logline: Mapped[str] = mapped_column(Text, default="")
    genre: Mapped[list] = mapped_column(JSON, default=list)
    subgenres: Mapped[list] = mapped_column(JSON, default=list)
    tone: Mapped[list] = mapped_column(JSON, default=list)
    target_audience: Mapped[str] = mapped_column(String(128), default="general")
    episode_count_target: Mapped[int] = mapped_column(Integer, default=3)
    episode_duration_target_seconds: Mapped[int] = mapped_column(Integer, default=75)
    aspect_ratio: Mapped[str] = mapped_column(String(16), default="9:16")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    project: Mapped["Project"] = relationship(back_populates="series")
    bible: Mapped["SeriesBible | None"] = relationship(back_populates="series", uselist=False, cascade="all, delete-orphan")
    characters: Mapped[list["Character"]] = relationship(back_populates="series", cascade="all, delete-orphan")
    relationships_: Mapped[list["RelationshipRecord"]] = relationship(back_populates="series", cascade="all, delete-orphan")
    knowledge_facts: Mapped[list["KnowledgeFactRecord"]] = relationship(back_populates="series", cascade="all, delete-orphan")
    episodes: Mapped[list["Episode"]] = relationship(back_populates="series", cascade="all, delete-orphan")
    season_plans: Mapped[list["SeasonPlanRecord"]] = relationship(back_populates="series", cascade="all, delete-orphan")


class SeriesBible(Base):
    __tablename__ = "series_bibles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    series_id: Mapped[str] = mapped_column(ForeignKey("series.id"), unique=True)
    premise: Mapped[str] = mapped_column(Text, default="")
    central_dramatic_question: Mapped[str] = mapped_column(Text, default="")
    protagonist_objective: Mapped[str] = mapped_column(Text, default="")
    primary_opposition: Mapped[str] = mapped_column(Text, default="")
    emotional_engine: Mapped[str] = mapped_column(Text, default="")
    themes: Mapped[list] = mapped_column(JSON, default=list)
    world_rules: Mapped[list] = mapped_column(JSON, default=list)
    central_secret: Mapped[str] = mapped_column(Text, default="")
    ending_target: Mapped[str] = mapped_column(Text, default="")
    prohibited_contradictions: Mapped[list] = mapped_column(JSON, default=list)
    locked_facts: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    series: Mapped["Series"] = relationship(back_populates="bible")


class SeasonPlanRecord(Base):
    """Versioned season/reveal map (Module 01 / XER-006).

    Each regeneration inserts a new row (never overwrites) so a rejected
    plan stays inspectable - same lineage philosophy as
    `ConceptCandidateRecord` (ADR-019). `version` is per-series and
    monotonically increasing; `status` tracks the inspect/regenerate/approve
    workflow.
    """

    __tablename__ = "season_plans"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    series_id: Mapped[str] = mapped_column(ForeignKey("series.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    plan: Mapped[dict] = mapped_column(JSON)
    qc_status: Mapped[str] = mapped_column(String(16), default="pass")
    qc_score: Mapped[float] = mapped_column(Float, default=0.0)
    qc_reasons: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    series: Mapped["Series"] = relationship(back_populates="season_plans")


class Character(Base):
    __tablename__ = "characters"

    # Character IDs are frequently proposed by the AI generator itself (e.g.
    # "CHAR_001") and referenced by later stages (episodes, shots) - see
    # docs/JSON_CONTRACTS.md Contract Rule 1. We persist the AI-proposed ID
    # directly rather than remapping, so a wider non-uuid-shaped key is
    # accepted here.
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_id)
    series_id: Mapped[str] = mapped_column(ForeignKey("series.id"))
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(64), default="")
    age: Mapped[str] = mapped_column(String(32), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    personality: Mapped[str] = mapped_column(Text, default="")
    goal: Mapped[str] = mapped_column(Text, default="")
    fear: Mapped[str] = mapped_column(Text, default="")
    flaw: Mapped[str] = mapped_column(Text, default="")
    secret: Mapped[str] = mapped_column(Text, default="")
    character_dna: Mapped[dict] = mapped_column(JSON, default=dict)
    visual_identity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    voice_identity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference_pack: Mapped[dict] = mapped_column(JSON, default=dict)
    identity_provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    series: Mapped["Series"] = relationship(back_populates="characters")


class CharacterWardrobeVariant(Base):
    """See research/CHARACTER_CONTINUITY_PLAYBOOK.md "Wardrobe as assets"."""

    __tablename__ = "character_wardrobe_variants"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    character_id: Mapped[str] = mapped_column(ForeignKey("characters.id"), index=True)
    label: Mapped[str] = mapped_column(String(128))
    reference_asset_ids: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class CharacterPhysicalStateVariant(Base):
    """See research/CHARACTER_CONTINUITY_PLAYBOOK.md "Physical State"."""

    __tablename__ = "character_physical_state_variants"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    character_id: Mapped[str] = mapped_column(ForeignKey("characters.id"), index=True)
    label: Mapped[str] = mapped_column(String(128))
    reference_asset_ids: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class RelationshipRecord(Base):
    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    series_id: Mapped[str] = mapped_column(ForeignKey("series.id"))
    source_character_id: Mapped[str] = mapped_column(String(64), ForeignKey("characters.id"))
    target_character_id: Mapped[str] = mapped_column(String(64), ForeignKey("characters.id"))
    relationship_type: Mapped[str] = mapped_column(String(64), default="")
    public_status: Mapped[str] = mapped_column(String(128), default="")
    private_status: Mapped[str] = mapped_column(String(128), default="")
    trust_level: Mapped[float] = mapped_column(Float, default=0.5)
    romantic_state: Mapped[str] = mapped_column(String(64), default="")
    valid_from_episode: Mapped[int] = mapped_column(Integer, default=1)
    valid_to_episode: Mapped[int | None] = mapped_column(Integer, nullable=True)

    series: Mapped["Series"] = relationship(back_populates="relationships_")


class KnowledgeFactRecord(Base):
    __tablename__ = "knowledge_facts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    series_id: Mapped[str] = mapped_column(ForeignKey("series.id"))
    statement: Mapped[str] = mapped_column(Text)
    truth_status: Mapped[str] = mapped_column(String(16), default="true")
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    introduced_episode: Mapped[int | None] = mapped_column(Integer, nullable=True)
    planned_reveal_episode: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_reveal_episode: Mapped[int | None] = mapped_column(Integer, nullable=True)
    knowledge: Mapped[dict] = mapped_column(JSON, default=dict)

    series: Mapped["Series"] = relationship(back_populates="knowledge_facts")


class Episode(Base):
    __tablename__ = "episodes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    series_id: Mapped[str] = mapped_column(ForeignKey("series.id"))
    episode_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255), default="")
    objective: Mapped[str] = mapped_column(Text, default="")
    opening_hook: Mapped[str] = mapped_column(Text, default="")
    central_conflict: Mapped[str] = mapped_column(Text, default="")
    turn: Mapped[str] = mapped_column(Text, default="")
    reveal: Mapped[str] = mapped_column(Text, default="")
    cliffhanger_type: Mapped[str] = mapped_column(String(64), default="")
    cliffhanger: Mapped[str] = mapped_column(Text, default="")
    duration_target_seconds: Mapped[int] = mapped_column(Integer, default=75)
    status: Mapped[str] = mapped_column(String(32), default="outlined")
    version: Mapped[int] = mapped_column(Integer, default=1)
    outline: Mapped[dict] = mapped_column(JSON, default=dict)
    script: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    series: Mapped["Series"] = relationship(back_populates="episodes")
    state_changes: Mapped[list["EpisodeStateChange"]] = relationship(
        back_populates="episode", cascade="all, delete-orphan"
    )
    scenes: Mapped[list["Scene"]] = relationship(back_populates="episode", cascade="all, delete-orphan")
    quality_reports: Mapped[list["QualityReport"]] = relationship(
        back_populates="episode", cascade="all, delete-orphan"
    )


class EpisodeStateChange(Base):
    __tablename__ = "episode_state_changes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    episode_id: Mapped[str] = mapped_column(ForeignKey("episodes.id"))
    change_type: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    committed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    episode: Mapped["Episode"] = relationship(back_populates="state_changes")


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    episode_id: Mapped[str] = mapped_column(ForeignKey("episodes.id"))
    scene_number: Mapped[int] = mapped_column(Integer)
    location: Mapped[str] = mapped_column(String(255), default="")
    time_of_day: Mapped[str] = mapped_column(String(32), default="")
    characters: Mapped[list] = mapped_column(JSON, default=list)
    objective: Mapped[str] = mapped_column(Text, default="")
    conflict: Mapped[str] = mapped_column(Text, default="")
    outcome: Mapped[str] = mapped_column(Text, default="")

    episode: Mapped["Episode"] = relationship(back_populates="scenes")
    shots: Mapped[list["Shot"]] = relationship(back_populates="scene", cascade="all, delete-orphan")


class Shot(Base):
    __tablename__ = "shots"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id"))
    shot_number: Mapped[int] = mapped_column(Integer)
    duration_seconds: Mapped[float] = mapped_column(Float, default=5.0)
    character_ids: Mapped[list] = mapped_column(JSON, default=list)
    narrative_function: Mapped[str] = mapped_column(String(128), default="")
    production_priority: Mapped[str] = mapped_column(String(16), default="normal")
    action: Mapped[str] = mapped_column(Text, default="")
    dialogue: Mapped[str] = mapped_column(Text, default="")
    camera: Mapped[dict] = mapped_column(JSON, default=dict)
    visual: Mapped[dict] = mapped_column(JSON, default=dict)
    blocking: Mapped[str] = mapped_column(Text, default="")
    blocking_plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    references: Mapped[dict] = mapped_column(JSON, default=dict)
    micro_beats: Mapped[list] = mapped_column(JSON, default=list)
    audio_mode: Mapped[str] = mapped_column(String(16), default="native")
    continuity_requirements: Mapped[list] = mapped_column(JSON, default=list)
    continuity_group: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    provider_requirements: Mapped[dict] = mapped_column(JSON, default=dict)
    generation_status: Mapped[str] = mapped_column(String(32), default="planned")

    scene: Mapped["Scene"] = relationship(back_populates="shots")


class QualityReport(Base):
    __tablename__ = "quality_reports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    episode_id: Mapped[str] = mapped_column(ForeignKey("episodes.id"))
    gate: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    repair_recommendation: Mapped[str] = mapped_column(Text, default="")
    dimensions: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    episode: Mapped["Episode"] = relationship(back_populates="quality_reports")


class GenerationJob(Base):
    """Persistent generation job. See docs/ARCHITECTURE.md section 11 and ADR-023."""

    __tablename__ = "generation_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    series_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    stage: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    provider: Mapped[str] = mapped_column(String(64), default="")
    model: Mapped[str] = mapped_column(String(128), default="")
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    error: Mapped[str] = mapped_column(Text, default="")
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    result_asset_ids: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    # Job-queue fields (MODULE-041) - additive, used only by the new
    # enqueue/claim/heartbeat path; the existing synchronous JobRunner
    # (create/start/succeed/fail) never touches these.
    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    depends_on_job_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(default=utcnow)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    lease_owner: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    project: Mapped["Project"] = relationship(back_populates="jobs")


class Asset(Base):
    """Persistent media asset - see ADR-020/022 and Module 04. The DB never
    holds the media bytes themselves (`storage_path` points into a
    `StorageProvider`); ownership is flattened into real columns because
    it's the main filter/join surface, provenance stays JSON."""

    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    type: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    storage_path: Mapped[str] = mapped_column(String(512))
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    mime_type: Mapped[str] = mapped_column(String(128), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    project_id: Mapped[str] = mapped_column(String(32), index=True)
    series_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    episode_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    character_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    scene_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shot_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    take_number: Mapped[int] = mapped_column(Integer, default=1)
    rejection_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class EpisodeRender(Base):
    """See MODULE-047. One row per render *version* - never overwritten;
    `status` (draft/approved/superseded) tracks which version is
    "current" (ADR-019)."""

    __tablename__ = "episode_renders"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    episode_id: Mapped[str] = mapped_column(ForeignKey("episodes.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    render_asset_id: Mapped[str] = mapped_column(String(32))
    parent_render_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_script_version: Mapped[int] = mapped_column(Integer)
    input_asset_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class MediaQCAttempt(Base):
    """See MODULE-044. Never overwritten - each QC pass on an asset (one
    dimension at a time) inserts a new row, giving a full audit trail
    (ADR-019's "preserve rejected takes and reasons" applied to QC
    attempts, not just generation takes)."""

    __tablename__ = "media_qc_attempts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    asset_id: Mapped[str] = mapped_column(String(32), index=True)
    dimension: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    repair_recommendation: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class StyleBible(Base):
    """One production-anchor row per series - see ADR-013 and Module 06."""

    __tablename__ = "style_bibles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    series_id: Mapped[str] = mapped_column(ForeignKey("series.id"), unique=True, index=True)
    style_asset_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    style_dna: Mapped[str] = mapped_column(Text, default="")
    palette: Mapped[list] = mapped_column(JSON, default=list)
    lighting: Mapped[str] = mapped_column(String(255), default="")
    texture: Mapped[str] = mapped_column(String(255), default="")
    color_temperature: Mapped[str] = mapped_column(String(255), default="")
    composition_rules: Mapped[list] = mapped_column(JSON, default=list)
    negatives: Mapped[list] = mapped_column(JSON, default=list)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Storyboard(Base):
    """Per-shot still-image workflow record - see Module 06. Individual
    keyframe attempts are `Asset` rows (type=image), not duplicated here."""

    __tablename__ = "storyboards"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    episode_id: Mapped[str] = mapped_column(ForeignKey("episodes.id"), index=True)
    scene_number: Mapped[int] = mapped_column(Integer)
    shot_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    layout_description: Mapped[str] = mapped_column(Text, default="")
    approved_keyframe_asset_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    auto_retake_attempts: Mapped[int] = mapped_column(Integer, default=0)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class ShotVideoProduction(Base):
    """Per-shot video workflow record - see Module 08. Individual takes are
    `Asset` rows (type=video), not duplicated here."""

    __tablename__ = "shot_video_productions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    episode_id: Mapped[str] = mapped_column(ForeignKey("episodes.id"), index=True)
    scene_number: Mapped[int] = mapped_column(Integer)
    shot_number: Mapped[int] = mapped_column(Integer)
    continuity_group: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    approved_take_asset_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    extracted_last_frame_asset_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    auto_retake_attempts: Mapped[int] = mapped_column(Integer, default=0)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class VoiceProfile(Base):
    """One row per character - see MODULE-034. Mirrors StyleBible's
    one-per-owner, lock/version (not full history) pattern."""

    __tablename__ = "voice_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    character_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), default="")
    provider_voice_id: Mapped[str] = mapped_column(String(128), default="")
    language: Mapped[str] = mapped_column(String(16), default="en")
    style: Mapped[str] = mapped_column(Text, default="")
    pronunciation_dictionary: Mapped[dict] = mapped_column(JSON, default=dict)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class ShotAudioProduction(Base):
    """Per-shot dialogue/audio workflow record - see MODULE-035.
    Individual takes are `Asset` rows (type=audio), not duplicated here."""

    __tablename__ = "shot_audio_productions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    episode_id: Mapped[str] = mapped_column(ForeignKey("episodes.id"), index=True)
    scene_number: Mapped[int] = mapped_column(Integer)
    shot_number: Mapped[int] = mapped_column(Integer)
    audio_mode: Mapped[str] = mapped_column(String(16), default="native")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    approved_take_asset_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    auto_retake_attempts: Mapped[int] = mapped_column(Integer, default=0)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class MusicCue(Base):
    """See MODULE-037. Cues are planning metadata + an asset pointer, not
    audio bytes themselves."""

    __tablename__ = "music_cues"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    episode_id: Mapped[str] = mapped_column(ForeignKey("episodes.id"), index=True)
    scene_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    purpose: Mapped[str] = mapped_column(String(128), default="")
    mood: Mapped[str] = mapped_column(String(128), default="")
    start_seconds: Mapped[float] = mapped_column(Float)
    end_seconds: Mapped[float] = mapped_column(Float)
    ducking_db: Mapped[float] = mapped_column(Float, default=0.0)
    asset_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rights: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class SoundEffectCue(Base):
    """See MODULE-038."""

    __tablename__ = "sound_effect_cues"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    episode_id: Mapped[str] = mapped_column(ForeignKey("episodes.id"), index=True)
    scene_number: Mapped[int] = mapped_column(Integer)
    shot_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    start_seconds: Mapped[float] = mapped_column(Float)
    end_seconds: Mapped[float] = mapped_column(Float)
    gain_db: Mapped[float] = mapped_column(Float, default=0.0)
    asset_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rights: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class SubtitleCue(Base):
    """See MODULE-039. `episode_id` + `language` identifies one subtitle
    track; regenerating replaces every cue for that (episode, language)
    pair rather than accumulating duplicates."""

    __tablename__ = "subtitle_cues"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    episode_id: Mapped[str] = mapped_column(ForeignKey("episodes.id"), index=True)
    scene_number: Mapped[int] = mapped_column(Integer)
    shot_number: Mapped[int] = mapped_column(Integer)
    character_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language: Mapped[str] = mapped_column(String(16), default="en", index=True)
    text: Mapped[str] = mapped_column(Text)
    lines: Mapped[list] = mapped_column(JSON, default=list)
    start_seconds: Mapped[float] = mapped_column(Float)
    end_seconds: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class CostRecord(Base):
    """See MODULE-049. One row per generation attempt - never updated.
    No prompt text/payload/secrets are ever stored here."""

    __tablename__ = "cost_records"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    stage: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    series_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    episode_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    scene_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shot_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(16), default="")
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_known: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    asset_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    failure_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class EpisodeMetric(Base):
    """See MODULE-061. One row per (episode, render_version, source,
    observation_window) - `MetricsRepository.upsert` updates the matching
    row rather than accumulating duplicates on re-import."""

    __tablename__ = "episode_metrics"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    episode_id: Mapped[str] = mapped_column(ForeignKey("episodes.id"), index=True)
    render_version: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(64), index=True)
    observation_window_start: Mapped[datetime] = mapped_column()
    observation_window_end: Mapped[datetime] = mapped_column()
    impressions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    views: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_watch_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    completion_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    three_second_retention_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    rewatch_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    continuation_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    engagement: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(default=utcnow)


class HumanFeedback(Base):
    """See MODULE-065. Append-only - every review decision is its own
    row, never overwritten, so feedback history survives a later
    re-review."""

    __tablename__ = "human_feedback"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    asset_id: Mapped[str] = mapped_column(String(32), index=True)
    project_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    decision: Mapped[str] = mapped_column(String(32))  # approved | rejected | retake_requested | edited
    reason: Mapped[str] = mapped_column(Text, default="")
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    reviewer: Mapped[str] = mapped_column(String(128), default="")
    provider: Mapped[str] = mapped_column(String(64), default="")
    model: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class EvalRunResult(Base):
    """See MODULE-072. Append-only - every benchmark run is its own row."""

    __tablename__ = "eval_run_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String(128), index=True)
    role: Mapped[str] = mapped_column(String(64), index=True)
    dataset_version: Mapped[str] = mapped_column(String(32), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128), index=True)
    schema_valid: Mapped[bool] = mapped_column(Boolean)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_reasons: Mapped[list] = mapped_column(JSON, default=list)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    raw_response_excerpt: Mapped[str] = mapped_column(Text, default="")
    human_preference: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class MediaEvalRunResult(Base):
    """See MODULE-073. Append-only - every benchmark run is its own row."""

    __tablename__ = "media_eval_run_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    case_id: Mapped[str] = mapped_column(String(128), index=True)
    shot_class: Mapped[str] = mapped_column(String(32), index=True)
    asset_type: Mapped[str] = mapped_column(String(16))
    dataset_version: Mapped[str] = mapped_column(String(32), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    generation_succeeded: Mapped[bool] = mapped_column(Boolean)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    qc_results: Mapped[list] = mapped_column(JSON, default=list)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    asset_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    human_preference: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class User(Base):
    """See MODULE-067. Only exists/matters in "hosted" mode - local
    single-user mode never creates a row here."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class AuthSession(Base):
    """See MODULE-067. An opaque bearer token - validity is a lookup +
    expiry check here, never signature verification."""

    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[datetime] = mapped_column()


class ProjectMembership(Base):
    """See MODULE-067. One row per (project_id, user_id) - `grant`
    upserts the role in place rather than accumulating duplicates."""

    __tablename__ = "project_memberships"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_membership"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # owner | editor | viewer
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
