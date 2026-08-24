from xerama.domain.scene import Camera, EpisodeShotPlan, Scene, Shot, Visual
from xerama.domain.subtitle import SubtitleCue
from xerama.pipeline.subtitle_generation import (
    cues_from_shot_plan,
    export_srt,
    format_srt_timestamp,
    wrap_subtitle_text,
)


def test_wrap_subtitle_text_short_line_stays_one_line() -> None:
    assert wrap_subtitle_text("This can't be real.") == ["This can't be real."]


def test_wrap_subtitle_text_wraps_long_line() -> None:
    text = "This is a much longer line of dialogue that will not fit on one row"
    lines = wrap_subtitle_text(text, max_chars_per_line=20)
    assert all(len(line) <= 20 for line in lines)
    assert " ".join(lines) == text


def test_wrap_subtitle_text_never_splits_a_single_long_word() -> None:
    lines = wrap_subtitle_text("supercalifragilisticexpialidocious", max_chars_per_line=10)
    assert lines == ["supercalifragilisticexpialidocious"]


def _shot(**overrides) -> Shot:
    base = dict(shot_number=1, scene_number=1, duration_seconds=5.0, camera=Camera(), visual=Visual())
    base.update(overrides)
    return Shot(**base)


def test_cues_from_shot_plan_skips_shots_without_dialogue() -> None:
    plan = EpisodeShotPlan(
        episode_number=1, scenes=[Scene(scene_number=1, location="apt", shots=[_shot(dialogue="")])]
    )
    assert cues_from_shot_plan(plan) == []


def test_cues_from_shot_plan_single_speaker_attributes_character() -> None:
    plan = EpisodeShotPlan(
        episode_number=1,
        scenes=[
            Scene(
                scene_number=1,
                location="apt",
                shots=[_shot(dialogue="This can't be real.", character_ids=["CHAR_001"])],
            )
        ],
    )
    cues = cues_from_shot_plan(plan)
    assert len(cues) == 1
    assert cues[0]["character_id"] == "CHAR_001"


def test_cues_from_shot_plan_multi_speaker_leaves_character_unset() -> None:
    plan = EpisodeShotPlan(
        episode_number=1,
        scenes=[
            Scene(
                scene_number=1,
                location="apt",
                shots=[_shot(dialogue="Overlapping.", character_ids=["CHAR_001", "CHAR_002"])],
            )
        ],
    )
    cues = cues_from_shot_plan(plan)
    assert cues[0]["character_id"] is None


def test_cues_from_shot_plan_accumulates_cumulative_timing_across_shots() -> None:
    plan = EpisodeShotPlan(
        episode_number=1,
        scenes=[
            Scene(
                scene_number=1,
                location="apt",
                shots=[
                    _shot(shot_number=1, duration_seconds=4.0, dialogue=""),  # no dialogue, still advances cursor
                    _shot(shot_number=2, duration_seconds=3.0, dialogue="Second line."),
                ],
            )
        ],
    )
    cues = cues_from_shot_plan(plan)
    assert len(cues) == 1
    assert cues[0]["start_seconds"] == 4.0
    assert cues[0]["end_seconds"] == 7.0


def test_format_srt_timestamp() -> None:
    assert format_srt_timestamp(0.0) == "00:00:00,000"
    assert format_srt_timestamp(65.5) == "00:01:05,500"
    assert format_srt_timestamp(3661.25) == "01:01:01,250"


def test_export_srt_formats_blocks_in_order_with_special_characters() -> None:
    cues = [
        SubtitleCue(
            id="c2",
            episode_id="EP_1",
            scene_number=1,
            shot_number=2,
            text="second",
            lines=["second"],
            start_seconds=5.0,
            end_seconds=6.0,
        ),
        SubtitleCue(
            id="c1",
            episode_id="EP_1",
            scene_number=1,
            shot_number=1,
            text="Café — \"quoted\" line, naïve?",
            lines=["Café — \"quoted\" line, naïve?"],
            start_seconds=0.0,
            end_seconds=2.0,
        ),
    ]
    srt = export_srt(cues)
    blocks = srt.strip().split("\n\n")
    assert len(blocks) == 2
    assert blocks[0].startswith("1\n00:00:00,000 --> 00:00:02,000\n")
    assert "Café — \"quoted\" line, naïve?" in blocks[0]
    assert blocks[1].startswith("2\n00:00:05,000 --> 00:00:06,000\n")
