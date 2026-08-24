from xerama.domain.enums import QCStatus
from xerama.domain.subtitle import SubtitleCue
from xerama.pipeline.subtitle_validators import SubtitleValidator


def _cue(**overrides) -> SubtitleCue:
    base = dict(
        id="c1",
        episode_id="EP_1",
        scene_number=1,
        shot_number=1,
        text="short line",
        lines=["short line"],
        start_seconds=0.0,
        end_seconds=5.0,
    )
    base.update(overrides)
    return SubtitleCue(**base)


def test_readability_passes_for_reasonable_cue() -> None:
    result = SubtitleValidator().check_readability([_cue()])
    assert result.status == QCStatus.PASS


def test_readability_warns_on_reading_speed_too_fast() -> None:
    long_text = "x" * 200
    cue = _cue(text=long_text, lines=[long_text[:32], long_text[32:64]], end_seconds=1.0)
    result = SubtitleValidator().check_readability([cue])
    assert result.status == QCStatus.WARN
    assert any("reading speed" in r for r in result.reasons)


def test_readability_warns_on_too_many_lines() -> None:
    cue = _cue(lines=["one", "two", "three"])
    result = SubtitleValidator().check_readability([cue])
    assert result.status == QCStatus.WARN
    assert any("exceeds the 2-line" in r for r in result.reasons)


def test_readability_warns_on_line_too_long() -> None:
    long_line = "x" * 50
    cue = _cue(lines=[long_line])
    result = SubtitleValidator().check_readability([cue])
    assert result.status == QCStatus.WARN
    assert any("exceeds 32 chars" in r for r in result.reasons)


def test_readability_warns_on_non_positive_duration() -> None:
    cue = _cue(start_seconds=2.0, end_seconds=2.0)
    result = SubtitleValidator().check_readability([cue])
    assert result.status == QCStatus.WARN
    assert any("non-positive duration" in r for r in result.reasons)
