"""Human feedback contract (MODULE-065).

"Human decisions become reusable evaluation data rather than disappearing
in chat/logs." Deliberately a separate record from `Asset.status`/
`rejection_reason` (Module 04) and `MediaQCAttempt` (MODULE-044) -
"separate subjective preference from objective QC failures": a
`MediaQCAttempt` is a deterministic/model-scored verdict, this is a
human's judgment call (rating, tags, free-text reason), and the two must
never be conflated into one record.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    # Domain contracts must not import xerama.db - see db/base.py's
    # documented boundary (MODULE-001 architecture audit).
    return datetime.now(timezone.utc)


class HumanFeedback(BaseModel):
    id: str
    asset_id: str
    project_id: str | None = None
    decision: str  # "approved" | "rejected" | "retake_requested" | "edited"
    reason: str = ""
    rating: int | None = Field(default=None, ge=1, le=5)
    tags: list[str] = Field(default_factory=list)
    reviewer: str = ""
    # Denormalized from the asset's provenance at feedback time - "link
    # feedback to exact artifact/take/version/model" without a join.
    provider: str = ""
    model: str = ""
    created_at: datetime = Field(default_factory=_utcnow)
