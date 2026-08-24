from xerama.providers.fake_image import FakeImageProvider
from xerama.providers.image import ImageEditRequest, ImageGenerationRequest, ImageProviderCapabilities


async def test_returns_queued_bytes_in_order() -> None:
    provider = FakeImageProvider([b"first", b"second"])
    request = ImageGenerationRequest(prompt="a shot")
    assert await provider.generate(request, []) == b"first"
    assert await provider.generate(request, []) == b"second"


async def test_returns_deterministic_placeholder_when_queue_empty() -> None:
    provider = FakeImageProvider()
    request = ImageGenerationRequest(prompt="a distinctive prompt")
    data = await provider.generate(request, [])
    assert b"a distinctive prompt" in data


async def test_records_calls_and_reference_count() -> None:
    provider = FakeImageProvider()
    request = ImageGenerationRequest(prompt="p")
    await provider.generate(request, [b"ref1", b"ref2"])
    assert len(provider.calls) == 1
    assert provider.calls[0][1] == 2


def test_default_capabilities() -> None:
    provider = FakeImageProvider()
    assert provider.capabilities.supported_aspects == ["9:16"]
    assert provider.capabilities.max_reference_images == 4


def test_custom_capabilities() -> None:
    caps = ImageProviderCapabilities(supported_aspects=["16:9"], max_reference_images=1)
    provider = FakeImageProvider(capabilities=caps)
    assert provider.capabilities.supported_aspects == ["16:9"]


async def test_edit_returns_queued_bytes() -> None:
    provider = FakeImageProvider([b"edited-image"])
    data = await provider.edit(ImageEditRequest(instruction="fix the hand"), b"base", None)
    assert data == b"edited-image"
    assert provider.edit_calls[0][0].instruction == "fix the hand"
    assert provider.edit_calls[0][1] is False


async def test_edit_returns_deterministic_placeholder_when_queue_empty() -> None:
    provider = FakeImageProvider()
    data = await provider.edit(ImageEditRequest(instruction="a distinctive fix"), b"base")
    assert b"a distinctive fix" in data


async def test_edit_records_whether_a_mask_was_supplied() -> None:
    provider = FakeImageProvider()
    await provider.edit(ImageEditRequest(instruction="i"), b"base", b"mask-bytes")
    assert provider.edit_calls[0][1] is True


def test_default_capabilities_do_not_support_edit() -> None:
    provider = FakeImageProvider()
    assert provider.capabilities.supports_edit is False
    assert provider.capabilities.supports_mask is False
