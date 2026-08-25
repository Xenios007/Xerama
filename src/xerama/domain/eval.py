"""AI evaluation run result contract (MODULE-072)."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from xerama.domain.enums import ModelRole


def _utcnow() -> datetime:
    # Domain contracts must not import xerama.db - see db/base.py's
    # documented boundary (MODULE-001 architecture audit).
    return datetime.now(timezone.utc)


class EvalRunResult(BaseModel):
    id: str
    case_id: str
    role: ModelRole
    dataset_version: str
    provider: str
    model: str
    schema_valid: bool
    quality_score: float | None = None
    quality_reasons: list[str] = Field(default_factory=list)
    latency_ms: float | None = None
    error: str = ""
    # Truncated - a debugging aid, never the source of truth for
    # reconstructing model behavior (that's `quality_reasons`, and the
    # per-attempt CostRecord ledger MODULE-049 already owns for
    # cost/latency/retry telemetry, not duplicated here).
    raw_response_excerpt: str = ""
    # Filled in later by a reviewer, never by the harness itself - a
    # human's judgment, not an automated measurement.
    human_preference: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
