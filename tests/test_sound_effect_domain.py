from xerama.domain.sound_effect import SoundEffectCue


def test_sound_effect_cue_defaults() -> None:
    cue = SoundEffectCue(id="SFX_1", episode_id="EP_1", scene_number=1, start_seconds=0.0, end_seconds=1.0)
    assert cue.status == "draft"
    assert cue.asset_id is None
    assert cue.shot_number is None
    assert cue.gain_db == 0.0


def test_sound_effect_cue_round_trips_through_json() -> None:
    cue = SoundEffectCue(
        id="SFX_1",
        episode_id="EP_1",
        scene_number=1,
        shot_number=2,
        description="door slams",
        start_seconds=1.0,
        end_seconds=1.5,
        gain_db=-3.0,
    )
    restored = SoundEffectCue.model_validate_json(cue.model_dump_json())
    assert restored.description == "door slams"
    assert restored.gain_db == -3.0
