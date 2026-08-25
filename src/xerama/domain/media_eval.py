"""Media evaluation run result contract (MODULE-073)."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from xerama.domain.asset import AssetType
from xerama.domain.enums import ShotClass


def _utcnow() -> datetime:
    # Domain contracts must not import xerama.db - see db/base.py's
    # documented boundary (MODULE-001 architecture audit).
    return datetime.now(timezone.utc)


class MediaQCDimensionResult(BaseModel):
    dimension: str
    status: str
    score: float


class MediaEvalRunResult(BaseModel):
    id: str
    case_id: str
    shot_class: ShotClass
    asset_type: AssetType
    dataset_version: str
    provider: str
    generation_succeeded: bool
    attempts: int = 0
    latency_ms: float | None = None
    # The provider's self-reported `capabilities.estimated_cost_usd` per
    # attempt - never a real billed amount (no media provider in this
    # codebase has a live usage-based cost API yet - MODULE-049's
    # CostRecord ledger already carries that honest "unknown unless a
    # real API reports it" distinction; this field is a *routing
    # estimate*, not billing telemetry, and is named accordingly).
    estimated_cost_usd: float | None = None
    qc_results: list[MediaQCDimensionResult] = Field(default_factory=list)
    accepted: bool = False
    asset_id: str | None = None
    error: str = ""
    human_preference: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
