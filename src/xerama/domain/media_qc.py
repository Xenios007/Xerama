"""Persisted multimodal QC verdicts (MODULE-044).

One row per QC attempt, never overwritten - the same "preserve every take
and its reasons" precedent as everywhere else in this codebase (ADR-019),
applied to QC passes rather than generation takes. `evidence` carries the
measurable facts (size/dimensions/duration, expectations compared against)
behind `reasons`, so a BLOCK/WARN is never just an opaque number (ADR-018).
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from xerama.domain.enums import MediaQCDimension, QCStatus


def _utcnow() -> datetime:
    # Domain contracts must not import xerama.db - see db/base.py's
    # documented boundary (MODULE-001 architecture audit).
    return datetime.now(timezone.utc)


class MediaQCAttempt(BaseModel):
    id: str
    asset_id: str
    dimension: MediaQCDimension
    status: QCStatus
    score: float = Field(ge=0, le=10)
    evidence: dict = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    repair_recommendation: str = ""
    created_at: datetime = Field(default_factory=_utcnow)
