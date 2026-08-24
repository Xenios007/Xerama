from xerama.domain.subtitle import SubtitleCue


def test_subtitle_cue_defaults() -> None:
    cue = SubtitleCue(
        id="SUB_1", episode_id="EP_1", scene_number=1, shot_number=1, text="hello", start_seconds=0.0, end_seconds=2.0
    )
    assert cue.language == "en"
    assert cue.character_id is None
    assert cue.lines == []


def test_subtitle_cue_round_trips_through_json() -> None:
    cue = SubtitleCue(
        id="SUB_1",
        episode_id="EP_1",
        scene_number=1,
        shot_number=1,
        character_id="CHAR_001",
        language="es",
        text="hola",
        lines=["hola"],
        start_seconds=1.0,
        end_seconds=3.0,
    )
    restored = SubtitleCue.model_validate_json(cue.model_dump_json())
    assert restored.language == "es"
    assert restored.lines == ["hola"]
