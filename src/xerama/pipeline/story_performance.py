"""Story performance learning (MODULE-063).

Joins persisted story metadata (today: `Cliffhanger.type` - the only
per-episode story-structure signal actually persisted; `hook`/`reversal`
are not separately scored/stored anywhere in this codebase yet, so this
does not fabricate numeric scores for them) to retention outcomes
(MODULE-062). Produces read-only advisory `StoryPerformanceInsight`s -
"keep learning suggestions separate from canonical state": nothing here
writes to `SeriesBible`/`CanonEvent`/any approved artifact, and a group
below the sample threshold is suppressed rather than surfaced as a weak
"pattern."
"""

from collections import defaultdict

from pydantic import BaseModel

from xerama.domain.enums import CliffhangerType
from xerama.pipeline.retention_analytics import RetentionSummary

MIN_SAMPLE_THRESHOLD = 3
HIGH_CONFIDENCE_THRESHOLD = 10


class StoryPerformanceInsight(BaseModel):
    dimension: str
    segment: str
    sample_count: int
    avg_completion_rate: float | None = None
    avg_continuation_rate: float | None = None
    confidence: str  # "medium" | "high" - below MIN_SAMPLE_THRESHOLD is suppressed entirely


def _average(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def analyze_cliffhanger_performance(
    episode_cliffhangers: list[tuple[str, CliffhangerType]],
    summaries_by_episode: dict[str, RetentionSummary],
) -> list[StoryPerformanceInsight]:
    by_type: dict[CliffhangerType, list[RetentionSummary]] = defaultdict(list)
    for episode_id, cliffhanger_type in episode_cliffhangers:
        summary = summaries_by_episode.get(episode_id)
        if summary is None or summary.sample_count == 0:
            continue
        by_type[cliffhanger_type].append(summary)

    insights: list[StoryPerformanceInsight] = []
    for cliffhanger_type in sorted(by_type, key=lambda t: t.value):
        summaries = by_type[cliffhanger_type]
        if len(summaries) < MIN_SAMPLE_THRESHOLD:
            continue
        insights.append(
            StoryPerformanceInsight(
                dimension="cliffhanger_type",
                segment=cliffhanger_type.value,
                sample_count=len(summaries),
                avg_completion_rate=_average([s.avg_completion_rate for s in summaries]),
                avg_continuation_rate=_average([s.avg_continuation_rate for s in summaries]),
                confidence="high" if len(summaries) >= HIGH_CONFIDENCE_THRESHOLD else "medium",
            )
        )
    return insights
