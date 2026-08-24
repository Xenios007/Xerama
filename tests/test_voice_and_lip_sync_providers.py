import pytest

from xerama.domain.enums import ProviderErrorKind
from xerama.providers.errors import ProviderError
from xerama.providers.fake_lip_sync import FakeLipSyncProvider
from xerama.providers.fake_voice import FakeVoiceProvider
from xerama.providers.lip_sync import LipSyncRequest
from xerama.providers.voice import VoiceGenerationRequest


async def test_fake_voice_provider_returns_queued_bytes() -> None:
    provider = FakeVoiceProvider([b"audio-1"])
    data = await provider.synthesize(VoiceGenerationRequest(text="hello"))
    assert data == b"audio-1"
    assert provider.calls[0].text == "hello"


async def test_fake_voice_provider_default_placeholder_is_deterministic() -> None:
    provider = FakeVoiceProvider()
    data = await provider.synthesize(VoiceGenerationRequest(text="a distinctive line"))
    assert b"a distinctive line" in data


async def test_fake_voice_provider_can_raise_queued_error() -> None:
    provider = FakeVoiceProvider([ProviderError(ProviderErrorKind.RATE_LIMIT, "slow down")])
    with pytest.raises(ProviderError):
        await provider.synthesize(VoiceGenerationRequest(text="hi"))


async def test_fake_lip_sync_provider_returns_queued_bytes() -> None:
    provider = FakeLipSyncProvider([b"synced-video"])
    data = await provider.sync(LipSyncRequest(), b"video", b"audio")
    assert data == b"synced-video"
    assert len(provider.calls) == 1


async def test_fake_lip_sync_provider_default_wraps_input_video() -> None:
    provider = FakeLipSyncProvider()
    data = await provider.sync(LipSyncRequest(), b"raw-video-bytes", b"audio")
    assert data == b"fake-lip-synced:raw-video-bytes"
