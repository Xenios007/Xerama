"""Retention analytics aggregation (MODULE-062).

Pure arithmetic over already-ingested `EpisodeMetric` rows (MODULE-061).
"Avoid inventing unavailable metrics": every averaged field is computed
only from the rows that actually reported it and is `None` (not 0) when
no row reported it at all - a missing metric must never look like a
metric of zero.
"""

from pydantic import BaseModel

from xerama.domain.analytics import EpisodeMetric
from xerama.domain.scene import EpisodeShotPlan


class RetentionSummary(BaseModel):
    episode_id: str
    sample_count: int
    sources: list[str]
    avg_completion_rate: float | None = None
    avg_three_second_retention_rate: float | None = None
    avg_watch_seconds: float | None = None
    avg_rewatch_rate: float | None = None
    avg_continuation_rate: float | None = None


class ShotDropPoint(BaseModel):
    scene_number: int
    shot_number: int
    timestamp_seconds: float
    viewers_remaining_pct: float


def _average(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def summarize_retention(episode_id: str, metrics: list[EpisodeMetric]) -> RetentionSummary:
    return RetentionSummary(
        episode_id=episode_id,
        sample_count=len(metrics),
        sources=sorted({m.source for m in metrics}),
        avg_completion_rate=_average([m.completion_rate for m in metrics]),
        avg_three_second_retention_rate=_average([m.three_second_retention_rate for m in metrics]),
        avg_watch_seconds=_average([m.avg_watch_seconds for m in metrics]),
        avg_rewatch_rate=_average([m.rewatch_rate for m in metrics]),
        avg_continuation_rate=_average([m.continuation_rate for m in metrics]),
    )


def map_drop_points_to_shots(
    metrics: list[EpisodeMetric], shot_plan: EpisodeShotPlan
) -> list[ShotDropPoint]:
    """"Link drop regions to episode timeline/shots where timestamps
    exist" - reads an optional `raw_payload["drop_points"]` list
    (`[{"timestamp_seconds": ..., "viewers_remaining_pct": ...}]`, a
    source-reported shape, not guaranteed) and maps each timestamp onto
    the shot whose cumulative-offset window contains it, using the same
    scene/shot-order cumulative-timing convention as
    `pipeline/subtitle_generation.py` and
    `pipeline/assembly_plan_builder.py`. Silently skips a drop point that
    falls outside every shot's window (e.g. post-roll) rather than
    guessing."""
    ordered_shots = sorted(
        ((scene.scene_number, shot) for scene in shot_plan.scenes for shot in scene.shots),
        key=lambda pair: (pair[0], pair[1].shot_number),
    )
    windows: list[tuple[int, int, float, float]] = []
    cursor = 0.0
    for scene_number, shot in ordered_shots:
        start = cursor
        end = cursor + shot.duration_seconds
        windows.append((scene_number, shot.shot_number, start, end))
        cursor = end

    results: list[ShotDropPoint] = []
    for metric in metrics:
        for point in metric.raw_payload.get("drop_points", []):
            timestamp = point.get("timestamp_seconds")
            pct = point.get("viewers_remaining_pct")
            if timestamp is None or pct is None:
                continue
            for scene_number, shot_number, start, end in windows:
                if start <= timestamp < end:
                    results.append(
                        ShotDropPoint(
                            scene_number=scene_number,
                            shot_number=shot_number,
                            timestamp_seconds=timestamp,
                            viewers_remaining_pct=pct,
                        )
                    )
                    break
    return results
