from xerama.domain.music import MusicCue


def test_music_cue_defaults() -> None:
    cue = MusicCue(id="MC_1", episode_id="EP_1", start_seconds=0.0, end_seconds=10.0)
    assert cue.status == "draft"
    assert cue.asset_id is None
    assert cue.rights.is_known is False
    assert cue.scene_number is None


def test_music_cue_round_trips_through_json() -> None:
    cue = MusicCue(
        id="MC_1",
        episode_id="EP_1",
        scene_number=2,
        purpose="tension build",
        mood="dread",
        start_seconds=5.0,
        end_seconds=15.0,
        ducking_db=-6.0,
        asset_id="asset-1",
    )
    restored = MusicCue.model_validate_json(cue.model_dump_json())
    assert restored.purpose == "tension build"
    assert restored.ducking_db == -6.0
    assert restored.asset_id == "asset-1"
