from datetime import datetime, timezone

import pytest

from xerama.domain.analytics import EpisodeMetric
from xerama.domain.enums import CliffhangerType
from xerama.domain.scene import Camera, EpisodeShotPlan, Scene, Shot, Visual
from xerama.pipeline.metrics_normalization import normalize_manual_payload
from xerama.pipeline.retention_analytics import map_drop_points_to_shots, summarize_retention
from xerama.pipeline.story_performance import (
    MIN_SAMPLE_THRESHOLD,
    analyze_cliffhanger_performance,
)
from xerama.pipeline.retention_analytics import RetentionSummary


def _metric(**overrides) -> EpisodeMetric:
    fields = dict(
        id="M1",
        episode_id="EP1",
        render_version=1,
        source="manual_import",
        observation_window_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        observation_window_end=datetime(2026, 8, 8, tzinfo=timezone.utc),
    )
    fields.update(overrides)
    return EpisodeMetric(**fields)


# --- metrics normalization (MODULE-061) -------------------------------------


def test_normalize_manual_payload_passes_through_known_fields() -> None:
    normalized = normalize_manual_payload(
        {"views": 1000, "completion_rate": 0.6, "unknown_field": "ignored"}
    )
    assert normalized["views"] == 1000
    assert normalized["completion_rate"] == 0.6
    assert normalized["impressions"] is None
    assert "unknown_field" not in normalized


def test_normalize_manual_payload_defaults_engagement_to_empty_dict() -> None:
    normalized = normalize_manual_payload({})
    assert normalized["engagement"] == {}


# --- retention analytics (MODULE-062) ----------------------------------------


def test_summarize_retention_averages_only_present_values() -> None:
    metrics = [
        _metric(id="M1", completion_rate=0.5, avg_watch_seconds=40.0),
        _metric(id="M2", completion_rate=0.7, avg_watch_seconds=None, source="tiktok_import"),
    ]
    summary = summarize_retention("EP1", metrics)
    assert summary.sample_count == 2
    assert summary.avg_completion_rate == pytest.approx(0.6)
    assert summary.avg_watch_seconds == pytest.approx(40.0)  # only the one present value
    assert summary.sources == ["manual_import", "tiktok_import"]


def test_summarize_retention_never_invents_missing_metrics() -> None:
    summary = summarize_retention("EP1", [_metric(completion_rate=None, avg_watch_seconds=None)])
    assert summary.avg_completion_rate is None
    assert summary.avg_watch_seconds is None


def test_summarize_retention_with_no_metrics() -> None:
    summary = summarize_retention("EP1", [])
    assert summary.sample_count == 0
    assert summary.avg_completion_rate is None


def _shot_plan() -> EpisodeShotPlan:
    return EpisodeShotPlan(
        episode_number=1,
        scenes=[
            Scene(
                scene_number=1,
                location="apartment",
                shots=[
                    Shot(shot_number=1, scene_number=1, action="a", duration_seconds=5.0, camera=Camera(), visual=Visual()),
                    Shot(shot_number=2, scene_number=1, action="b", duration_seconds=5.0, camera=Camera(), visual=Visual()),
                ],
            )
        ],
    )


def test_map_drop_points_to_shots_finds_the_containing_shot() -> None:
    metric = _metric(
        raw_payload={"drop_points": [{"timestamp_seconds": 7.0, "viewers_remaining_pct": 0.4}]}
    )
    points = map_drop_points_to_shots([metric], _shot_plan())
    assert len(points) == 1
    assert points[0].scene_number == 1
    assert points[0].shot_number == 2  # shot 2 spans [5, 10)
    assert points[0].viewers_remaining_pct == 0.4


def test_map_drop_points_to_shots_skips_out_of_range_timestamps() -> None:
    metric = _metric(
        raw_payload={"drop_points": [{"timestamp_seconds": 100.0, "viewers_remaining_pct": 0.1}]}
    )
    assert map_drop_points_to_shots([metric], _shot_plan()) == []


def test_map_drop_points_to_shots_handles_missing_drop_points() -> None:
    assert map_drop_points_to_shots([_metric()], _shot_plan()) == []


# --- story performance learning (MODULE-063) ---------------------------------


def test_analyze_cliffhanger_performance_suppresses_below_threshold() -> None:
    episodes = [("EP1", CliffhangerType.IDENTITY_REVEAL), ("EP2", CliffhangerType.IDENTITY_REVEAL)]
    summaries = {
        "EP1": RetentionSummary(episode_id="EP1", sample_count=1, sources=["m"], avg_completion_rate=0.8),
        "EP2": RetentionSummary(episode_id="EP2", sample_count=1, sources=["m"], avg_completion_rate=0.6),
    }
    assert len(episodes) < MIN_SAMPLE_THRESHOLD
    insights = analyze_cliffhanger_performance(episodes, summaries)
    assert insights == []


def test_analyze_cliffhanger_performance_surfaces_pattern_at_threshold() -> None:
    episodes = [(f"EP{i}", CliffhangerType.THREAT) for i in range(MIN_SAMPLE_THRESHOLD)]
    summaries = {
        f"EP{i}": RetentionSummary(
            episode_id=f"EP{i}", sample_count=1, sources=["m"], avg_completion_rate=0.5 + i * 0.1
        )
        for i in range(MIN_SAMPLE_THRESHOLD)
    }
    insights = analyze_cliffhanger_performance(episodes, summaries)
    assert len(insights) == 1
    assert insights[0].segment == "threat"
    assert insights[0].sample_count == MIN_SAMPLE_THRESHOLD
    assert insights[0].confidence == "medium"


def test_analyze_cliffhanger_performance_ignores_episodes_with_no_metrics() -> None:
    episodes = [(f"EP{i}", CliffhangerType.THREAT) for i in range(MIN_SAMPLE_THRESHOLD)]
    summaries = {
        f"EP{i}": RetentionSummary(episode_id=f"EP{i}", sample_count=0, sources=[])
        for i in range(MIN_SAMPLE_THRESHOLD)
    }
    assert analyze_cliffhanger_performance(episodes, summaries) == []
