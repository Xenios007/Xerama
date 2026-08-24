from xerama.domain.scene import MicroBeat


def test_micro_beat_defaults() -> None:
    beat = MicroBeat(start_seconds=0.0, end_seconds=2.0, description="Mara looks up")
    assert beat.character_id is None
    assert beat.pose == ""
    assert beat.expression == ""
    assert beat.gaze == ""
    assert beat.camera_note == ""


def test_micro_beat_structured_performance_fields() -> None:
    beat = MicroBeat(
        start_seconds=0.0,
        end_seconds=2.0,
        description="Mara reads the letter",
        character_id="CHAR_001",
        pose="leaning over the table",
        expression="dread",
        gaze="down at the page",
        camera_note="slow push in",
    )
    restored = MicroBeat.model_validate_json(beat.model_dump_json())
    assert restored.character_id == "CHAR_001"
    assert restored.pose == "leaning over the table"
    assert restored.expression == "dread"
    assert restored.gaze == "down at the page"
    assert restored.camera_note == "slow push in"
