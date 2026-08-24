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
from xerama.domain.brief import CreativeBrief
from xerama.domain.canon import CanonEvent
from xerama.domain.character import Character, CharacterCast, PhysicalStateVariant, WardrobeVariant
from xerama.domain.episode import EpisodeOutline, EpisodeScript
from xerama.domain.quality import QCResult
from xerama.domain.scene import EpisodeShotPlan
from xerama.domain.season import SeasonPlan
from xerama.domain.storyboard import Storyboard
from xerama.domain.story import ConceptCandidate, JudgeResult
from xerama.domain.style_bible import StyleBible
from xerama.domain.video_production import ShotVideoProduction
from xerama.domain.enums import JobStage, JobStatus


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


class ProjectRepository(Protocol):
    async def create(self, name: str, description: str = "") -> ProjectRecord: ...
    async def get(self, project_id: str) -> ProjectRecord | None: ...


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


class SeriesRepository(Protocol):
    async def create_series(
        self, project_id: str, brief: CreativeBrief, approved_concept: ConceptCandidate
    ) -> SeriesRecord: ...

    async def get_series(self, series_id: str) -> SeriesRecord | None: ...

    async def save_bible(self, series_id: str, bible) -> None: ...

    async def get_bible(self, series_id: str): ...

    async def save_cast(self, series_id: str, cast: CharacterCast) -> None: ...

    async def get_cast(self, series_id: str) -> CharacterCast: ...


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
    ) -> list[Asset]: ...

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
