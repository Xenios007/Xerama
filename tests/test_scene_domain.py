import pytest
from pydantic import ValidationError

from xerama.domain.scene import Camera, ProviderRequirements, Scene, Shot, Visual


def _shot(**overrides) -> Shot:
    base = dict(shot_number=1, scene_number=1, duration_seconds=5.0)
    base.update(overrides)
    return Shot(**base)


def test_shot_defaults_are_provider_neutral_and_independent() -> None:
    shot = _shot()
    assert shot.continuity_group is None
    assert shot.blocking == ""
    assert shot.provider_requirements == ProviderRequirements()
    assert shot.provider_requirements.image_to_video is True
    assert shot.provider_requirements.text_to_video is False


def test_shot_requires_positive_duration() -> None:
    with pytest.raises(ValidationError):
        _shot(duration_seconds=0)


def test_shot_accepts_continuity_group_and_provider_requirements() -> None:
    shot = _shot(
        continuity_group="GRP_A",
        provider_requirements=ProviderRequirements(last_frame_required=True, native_audio_required=True),
        blocking="A left, B right",
    )
    assert shot.continuity_group == "GRP_A"
    assert shot.provider_requirements.last_frame_required is True
    assert shot.provider_requirements.native_audio_required is True
    assert shot.blocking == "A left, B right"


def test_scene_round_trip_with_shots() -> None:
    scene = Scene(
        scene_number=1,
        location="apartment",
        shots=[_shot(camera=Camera(shot_size="close-up"), visual=Visual(emotion="dread"))],
    )
    restored = Scene.model_validate_json(scene.model_dump_json())
    assert restored.shots[0].camera.shot_size == "close-up"
    assert restored.shots[0].visual.emotion == "dread"
