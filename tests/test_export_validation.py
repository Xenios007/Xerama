from xerama.domain.assembly import OutputSpec
from xerama.domain.enums import QCStatus
from xerama.domain.export import MediaProbeResult
from xerama.domain.subtitle import SubtitleCue
from xerama.pipeline.export_validation import validate_export


def _spec(**overrides) -> OutputSpec:
    fields = dict(width=1080, height=1920, fps=30)
    fields.update(overrides)
    return OutputSpec(**fields)


def test_matching_probe_passes() -> None:
    probe = MediaProbeResult(
        ok=True, duration_seconds=10.0, width=1080, height=1920,
        has_video_stream=True, has_audio_stream=True,
    )
    result = validate_export(probe, _spec(), expected_duration_seconds=10.0)
    assert result.status == QCStatus.PASS
    assert result.reasons == []


def test_ffprobe_failure_blocks() -> None:
    probe = MediaProbeResult(ok=False, error="invalid data found")
    result = validate_export(probe, _spec())
    assert result.status == QCStatus.BLOCK
    assert result.score == 0.0
    assert "ffprobe could not read" in result.reasons[0]


def test_missing_video_stream_blocks() -> None:
    probe = MediaProbeResult(ok=True, has_video_stream=False, has_audio_stream=True)
    result = validate_export(probe, _spec())
    assert result.status == QCStatus.BLOCK
    assert "no video stream" in result.reasons[0]


def test_missing_audio_stream_warns_not_blocks() -> None:
    probe = MediaProbeResult(
        ok=True, duration_seconds=5.0, width=1080, height=1920,
        has_video_stream=True, has_audio_stream=False,
    )
    result = validate_export(probe, _spec(), expected_duration_seconds=5.0)
    assert result.status == QCStatus.WARN
    assert "no audio stream" in result.reasons[0]


def test_resolution_mismatch_warns() -> None:
    probe = MediaProbeResult(
        ok=True, duration_seconds=5.0, width=1920, height=1080,
        has_video_stream=True, has_audio_stream=True,
    )
    result = validate_export(probe, _spec(width=1080, height=1920), expected_duration_seconds=5.0)
    assert result.status == QCStatus.WARN
    assert any("resolution" in r for r in result.reasons)


def test_duration_mismatch_warns() -> None:
    probe = MediaProbeResult(
        ok=True, duration_seconds=20.0, width=1080, height=1920,
        has_video_stream=True, has_audio_stream=True,
    )
    result = validate_export(probe, _spec(), expected_duration_seconds=5.0)
    assert result.status == QCStatus.WARN
    assert any("duration" in r for r in result.reasons)


def test_unmeasured_fields_warn_not_block() -> None:
    """No real ffprobe wired up yet - missing data is a soft signal, not
    proof of a broken file (same precedent as MODULE-044's deterministic
    checks)."""
    probe = MediaProbeResult(ok=True, has_video_stream=True, has_audio_stream=True)
    result = validate_export(probe, _spec())
    assert result.status == QCStatus.WARN


def test_subtitle_readability_issues_are_folded_in_as_warnings() -> None:
    probe = MediaProbeResult(
        ok=True, duration_seconds=5.0, width=1080, height=1920,
        has_video_stream=True, has_audio_stream=True,
    )
    cues = [
        SubtitleCue(
            id="C1", episode_id="EP1", scene_number=1, shot_number=1,
            text="x" * 100, lines=["x" * 100], start_seconds=0.0, end_seconds=1.0,
        )
    ]
    result = validate_export(probe, _spec(), expected_duration_seconds=5.0, subtitle_cues=cues)
    assert result.status == QCStatus.WARN
    assert any("subtitle safe-area" in r for r in result.reasons)
