import pytest

from xerama.domain.assembly import OutputSpec
from xerama.domain.audio_production import ShotAudioProduction
from xerama.domain.enums import AudioMode
from xerama.domain.music import MusicCue
from xerama.domain.scene import Camera, EpisodeShotPlan, Scene, Shot, Visual
from xerama.domain.sound_effect import SoundEffectCue
from xerama.domain.video_production import ShotVideoProduction
from xerama.pipeline.assembly_plan_builder import IncompleteProductionError, build_assembly_plan


def _shot(shot_number: int, scene_number: int = 1, duration_seconds: float = 5.0, **overrides) -> Shot:
    fields = dict(
        shot_number=shot_number,
        scene_number=scene_number,
        character_ids=["CHAR_001"],
        action="does something",
        duration_seconds=duration_seconds,
        camera=Camera(shot_size="close-up"),
        visual=Visual(),
    )
    fields.update(overrides)
    return Shot(**fields)


def _plan(*shots: Shot) -> EpisodeShotPlan:
    return EpisodeShotPlan(
        episode_number=1,
        scenes=[Scene(scene_number=1, location="apartment", characters=["CHAR_001"], shots=list(shots))],
    )


def _video_production(scene_number: int, shot_number: int, asset_id: str = "VID1") -> ShotVideoProduction:
    return ShotVideoProduction(
        id=f"VP_{scene_number}_{shot_number}",
        episode_id="EP1",
        scene_number=scene_number,
        shot_number=shot_number,
        status="approved",
        approved_take_asset_id=asset_id,
    )


def test_native_shot_needs_no_separate_audio_track() -> None:
    plan = _plan(_shot(1, audio_mode=AudioMode.NATIVE, duration_seconds=5.0))
    result = build_assembly_plan("EP1", plan, [_video_production(1, 1)], [], [], [])
    assert len(result.clips) == 1
    assert result.clips[0].start_seconds == 0.0
    assert result.audio_tracks == []
    assert result.total_duration_seconds == 5.0


def test_tts_lipsync_shot_needs_no_separate_audio_track() -> None:
    """Lip-synced video already has the dialogue audio baked in."""
    plan = _plan(_shot(1, audio_mode=AudioMode.TTS_LIPSYNC))
    result = build_assembly_plan("EP1", plan, [_video_production(1, 1)], [], [], [])
    assert result.audio_tracks == []


def test_hybrid_shot_requires_approved_dialogue_track() -> None:
    plan = _plan(_shot(1, audio_mode=AudioMode.HYBRID))
    with pytest.raises(IncompleteProductionError, match="hybrid"):
        build_assembly_plan("EP1", plan, [_video_production(1, 1)], [], [], [])


def test_hybrid_shot_adds_dialogue_audio_track() -> None:
    plan = _plan(_shot(1, audio_mode=AudioMode.HYBRID, duration_seconds=5.0))
    audio_production = ShotAudioProduction(
        id="AP1", episode_id="EP1", scene_number=1, shot_number=1,
        audio_mode=AudioMode.HYBRID, status="approved", approved_take_asset_id="AUD1",
    )
    result = build_assembly_plan("EP1", plan, [_video_production(1, 1)], [audio_production], [], [])
    assert len(result.audio_tracks) == 1
    assert result.audio_tracks[0].kind == "dialogue"
    assert result.audio_tracks[0].asset_id == "AUD1"
    assert result.audio_tracks[0].start_seconds == 0.0
    assert result.audio_tracks[0].end_seconds == 5.0


def test_missing_video_take_raises_incomplete_production_error() -> None:
    plan = _plan(_shot(1))
    with pytest.raises(IncompleteProductionError):
        build_assembly_plan("EP1", plan, [], [], [], [])


def test_clips_positioned_at_cumulative_offsets() -> None:
    plan = _plan(_shot(1, duration_seconds=5.0), _shot(2, duration_seconds=3.0))
    video_productions = [_video_production(1, 1, "VID1"), _video_production(1, 2, "VID2")]
    result = build_assembly_plan("EP1", plan, video_productions, [], [], [])
    assert result.clips[0].start_seconds == 0.0
    assert result.clips[1].start_seconds == 5.0
    assert result.total_duration_seconds == 8.0


def test_only_approved_music_and_sfx_cues_are_included() -> None:
    plan = _plan(_shot(1))
    music_cues = [
        MusicCue(id="M1", episode_id="EP1", start_seconds=0, end_seconds=5, asset_id="MUS1", status="approved"),
        MusicCue(id="M2", episode_id="EP1", start_seconds=0, end_seconds=5, asset_id="MUS2", status="draft"),
        MusicCue(id="M3", episode_id="EP1", start_seconds=0, end_seconds=5, asset_id=None, status="approved"),
    ]
    sfx_cues = [
        SoundEffectCue(
            id="S1", episode_id="EP1", scene_number=1, start_seconds=1, end_seconds=2,
            asset_id="SFX1", status="approved",
        ),
        SoundEffectCue(
            id="S2", episode_id="EP1", scene_number=1, start_seconds=1, end_seconds=2,
            asset_id="SFX2", status="draft",
        ),
    ]
    result = build_assembly_plan("EP1", plan, [_video_production(1, 1)], [], music_cues, sfx_cues)
    kinds_and_ids = {(t.kind, t.asset_id) for t in result.audio_tracks}
    assert kinds_and_ids == {("music", "MUS1"), ("sfx", "SFX1")}


def test_music_ducking_becomes_negative_gain() -> None:
    plan = _plan(_shot(1))
    music_cues = [
        MusicCue(
            id="M1", episode_id="EP1", start_seconds=0, end_seconds=5,
            asset_id="MUS1", status="approved", ducking_db=6.0,
        )
    ]
    result = build_assembly_plan("EP1", plan, [_video_production(1, 1)], [], music_cues, [])
    assert result.audio_tracks[0].gain_db == -6.0


def test_default_output_spec_is_vertical() -> None:
    plan = _plan(_shot(1))
    result = build_assembly_plan("EP1", plan, [_video_production(1, 1)], [], [], [])
    assert result.output.aspect_ratio == "9:16"
    assert result.output.width == 1080
    assert result.output.height == 1920


def test_custom_output_spec_is_honored() -> None:
    plan = _plan(_shot(1))
    output = OutputSpec(width=720, height=1280, fps=24)
    result = build_assembly_plan("EP1", plan, [_video_production(1, 1)], [], [], [], output=output)
    assert result.output.width == 720
    assert result.output.fps == 24
