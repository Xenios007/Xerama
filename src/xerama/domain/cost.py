"""Production cost telemetry contract (MODULE-049).

Supersedes the earlier "AI-call telemetry is disabled for this build"
deviation (see docs/IMPLEMENTATION_STATUS.md, originally overriding
ADR-010's "extremely important" per one session's explicit direction) -
the MODULE-001..080 queue now explicitly commissions this as MODULE-049,
so it is built and the deviation note is marked superseded rather than
silently re-diverging from the architecture freeze.

One row per generation attempt (LLM or media), never updated - the same
append-only-ledger precedent as `MediaQCAttempt`/every take-numbered
`Asset`. Deliberately carries no prompt text, payload bytes, or secrets -
"keep secrets/raw sensitive payloads out" is satisfied by the schema
simply having no field for them.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    # Domain contracts must not import xerama.db - see db/base.py's
    # documented boundary (MODULE-001 architecture audit).
    return datetime.now(timezone.utc)


class CostRecord(BaseModel):
    id: str
    provider: str
    model: str
    stage: str  # a JobStage value, or a media-pipeline stage label
    project_id: str | None = None
    series_id: str | None = None
    episode_id: str | None = None
    scene_number: int | None = None
    shot_number: int | None = None
    attempt: int = 1
    # Generic usage measure - tokens (LLM), seconds (video/audio),
    # characters (voice), or a flat 1 (one image) - `unit` disambiguates.
    quantity: float = 0.0
    unit: str = ""  # "tokens" | "seconds" | "characters" | "images"
    # `cost_known=False` means "no live pricing integration for this
    # provider/model yet" (every provider in this codebase today) -
    # distinct from `cost_usd=0.0` which means "confirmed free/no charge".
    cost_usd: float | None = None
    cost_known: bool = False
    latency_ms: float | None = None
    asset_id: str | None = None
    failure_reason: str = ""
    created_at: datetime = Field(default_factory=_utcnow)
