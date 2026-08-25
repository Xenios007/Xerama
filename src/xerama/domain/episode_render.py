"""Episode render versioning contract (MODULE-047).

Mirrors `domain/storyboard.py`'s lightweight per-owner workflow-record
pattern, extended with a third `superseded` status so "current" is an
explicit, single-row invariant rather than "whichever is latest and still
approved" (`SeasonPlanRecord`'s precedent) - that ambiguity would make
rollback (re-approving an older version) impossible to distinguish from
"nothing changed." Every render is a new row, never overwritten or
deleted (ADR-019/"never overwrite a published/approved version silently")
- rollback re-approves an existing `superseded` row rather than mutating
anything.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    # Domain contracts must not import xerama.db - see db/base.py's
    # documented boundary (MODULE-001 architecture audit).
    return datetime.now(timezone.utc)


class EpisodeRender(BaseModel):
    id: str
    episode_id: str
    version: int
    status: str = "draft"  # draft | approved | superseded
    render_asset_id: str
    parent_render_id: str | None = None
    # Staleness inputs - see `pipeline/render_staleness.py:check_staleness`.
    # Captured at render time, immutable afterward.
    source_script_version: int
    input_asset_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
