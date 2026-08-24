"""Asset & Storage domain contracts (Module 04).

The persistent media foundation used by every future provider (image,
video, voice, lip-sync, editor). See ADR-020 (generated assets must be
persisted immediately - provider URLs are not archival storage) and
ADR-022 (local storage first, S3-compatible later).
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from xerama.db.base import utcnow


class AssetType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    DOCUMENT = "document"
    OTHER = "other"


class AssetStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class AssetOwnership(BaseModel):
    """Where in the production hierarchy this asset belongs. Only
    `project_id` is required - everything below it narrows as the asset's
    origin gets more specific."""

    project_id: str
    series_id: str | None = None
    episode_id: str | None = None
    scene_number: int | None = None
    shot_number: int | None = None


class AssetProvenance(BaseModel):
    """Lineage metadata - see ADR-010/020 and docs/DATA_MODEL.md asset lineage."""

    provider: str = ""
    model: str = ""
    prompt_version: str = ""
    generation_params: dict = Field(default_factory=dict)
    source_reference_asset_ids: list[str] = Field(default_factory=list)
    # The provider URL this was ingested from, kept only for audit - never
    # relied on for retrieval after ingest (ADR-020).
    source_url: str | None = None


class Asset(BaseModel):
    id: str
    type: AssetType
    status: AssetStatus = AssetStatus.PENDING
    storage_path: str
    content_hash: str
    mime_type: str = ""
    size_bytes: int = 0
    width: int | None = None
    height: int | None = None
    duration_seconds: float | None = None
    ownership: AssetOwnership
    provenance: AssetProvenance = Field(default_factory=AssetProvenance)
    take_number: int = 1
    rejection_reason: str = ""
    created_at: datetime = Field(default_factory=utcnow)
