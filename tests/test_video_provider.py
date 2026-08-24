from xerama.domain.scene import ProviderRequirements
from xerama.providers.errors import ProviderError
from xerama.providers.fake_video import FakeVideoProvider
from xerama.providers.video import VideoGenerationRequest, VideoProviderCapabilities, matches_requirements


async def test_fake_video_provider_returns_queued_bytes() -> None:
    provider = FakeVideoProvider([b"clip-1"])
    data = await provider.generate(VideoGenerationRequest(prompt="a shot"), [])
    assert data == b"clip-1"
    assert len(provider.calls) == 1


async def test_fake_video_provider_can_raise_queued_error() -> None:
    import pytest
    from xerama.domain.enums import ProviderErrorKind

    provider = FakeVideoProvider([ProviderError(ProviderErrorKind.TIMEOUT, "slow")])
    with pytest.raises(ProviderError):
        await provider.generate(VideoGenerationRequest(prompt="p"), [])


def test_matches_requirements_rejects_unsupported_aspect() -> None:
    caps = VideoProviderCapabilities(supported_aspects=["16:9"])
    assert matches_requirements(caps, ProviderRequirements(), aspect_ratio="9:16") is False


def test_matches_requirements_rejects_duration_over_max() -> None:
    caps = VideoProviderCapabilities(max_duration_seconds=5.0)
    assert matches_requirements(caps, ProviderRequirements(), duration_seconds=8.0) is False


def test_matches_requirements_rejects_missing_last_frame_support() -> None:
    caps = VideoProviderCapabilities(last_frame=False)
    requirements = ProviderRequirements(last_frame_required=True)
    assert matches_requirements(caps, requirements) is False


def test_matches_requirements_rejects_missing_native_audio() -> None:
    caps = VideoProviderCapabilities(native_audio=False)
    requirements = ProviderRequirements(native_audio_required=True)
    assert matches_requirements(caps, requirements) is False


def test_matches_requirements_accepts_compatible_provider() -> None:
    caps = VideoProviderCapabilities(
        last_frame=True, native_audio=True, subject_reference=True, max_duration_seconds=15.0
    )
    requirements = ProviderRequirements(
        last_frame_required=True, native_audio_required=True, subject_reference_required=True
    )
    assert matches_requirements(caps, requirements, duration_seconds=10.0) is True
