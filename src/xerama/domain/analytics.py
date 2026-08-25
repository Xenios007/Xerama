"""Post-publication performance analytics contracts (MODULE-061).

Provider/platform-neutral: a metric row attaches to the exact published
`EpisodeRender` version (MODULE-047), never just "the episode," so
performance data always traces to specific rendered assets even after a
re-render supersedes it. Every normalized field is optional - `None`
means "this source didn't report it," never a fabricated 0 (MODULE-062's
"avoid inventing unavailable metrics" starts with the schema itself).
`raw_payload` preserves the exact import for audit ("preserve raw-source
provenance").
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    # Domain contracts must not import xerama.db - see db/base.py's
    # documented boundary (MODULE-001 architecture audit).
    return datetime.now(timezone.utc)


class EpisodeMetric(BaseModel):
    id: str
    episode_id: str
    render_version: int
    source: str  # "manual_import" today; a real platform-API source name later
    observation_window_start: datetime
    observation_window_end: datetime
    impressions: int | None = None
    views: int | None = None
    avg_watch_seconds: float | None = None
    completion_rate: float | None = None  # 0-1
    three_second_retention_rate: float | None = None  # 0-1
    rewatch_rate: float | None = None  # 0-1
    continuation_rate: float | None = None  # 0-1, viewers continuing to the next episode
    engagement: dict = Field(default_factory=dict)  # source-defined (likes/comments/shares/...)
    raw_payload: dict = Field(default_factory=dict)
    imported_at: datetime = Field(default_factory=_utcnow)
