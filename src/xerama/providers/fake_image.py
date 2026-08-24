"""In-memory fake `ImageProvider` for tests and local runs without a paid
API call - same pattern as `providers/fake.py`'s `FakeLLMProvider`.
"""

from collections import deque

from xerama.providers.image import ImageGenerationRequest, ImageProviderCapabilities


class FakeImageProvider:
    """Returns pre-scripted image bytes in call order, or a deterministic
    placeholder if nothing was queued. Every call is recorded in `.calls`
    (request + how many reference images were supplied) for assertions."""

    def __init__(
        self,
        responses: list[bytes] | None = None,
        capabilities: ImageProviderCapabilities | None = None,
    ) -> None:
        self._queue: deque[bytes] = deque(responses or [])
        self._capabilities = capabilities or ImageProviderCapabilities()
        self.calls: list[tuple[ImageGenerationRequest, int]] = []

    def queue(self, data: bytes) -> None:
        self._queue.append(data)

    @property
    def name(self) -> str:
        return "fake_image"

    @property
    def capabilities(self) -> ImageProviderCapabilities:
        return self._capabilities

    async def generate(self, request: ImageGenerationRequest, reference_images: list[bytes]) -> bytes:
        self.calls.append((request, len(reference_images)))
        if self._queue:
            return self._queue.popleft()
        return f"fake-image:{request.prompt}".encode()
