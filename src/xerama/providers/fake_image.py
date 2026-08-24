"""In-memory fake `ImageProvider` for tests and local runs without a paid
API call - same pattern as `providers/fake.py`'s `FakeLLMProvider`.
"""

from collections import deque

from xerama.providers.errors import ProviderError
from xerama.providers.image import ImageEditRequest, ImageGenerationRequest, ImageProviderCapabilities


class FakeImageProvider:
    """Returns pre-scripted image bytes (or raises a queued `ProviderError`)
    in call order, or a deterministic placeholder if nothing was queued.
    `generate` and `edit` share one response queue (attempts happen in
    real chronological order regardless of which call made them). Every
    call is recorded in `.calls`/`.edit_calls` for assertions."""

    def __init__(
        self,
        responses: list[bytes | ProviderError] | None = None,
        capabilities: ImageProviderCapabilities | None = None,
        name: str = "fake_image",
    ) -> None:
        self._queue: deque[bytes | ProviderError] = deque(responses or [])
        self._capabilities = capabilities or ImageProviderCapabilities()
        self._name = name
        self.calls: list[tuple[ImageGenerationRequest, int]] = []
        self.edit_calls: list[tuple[ImageEditRequest, bool]] = []

    def queue(self, item: bytes | ProviderError) -> None:
        self._queue.append(item)

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> ImageProviderCapabilities:
        return self._capabilities

    def _next(self, default: bytes) -> bytes:
        if self._queue:
            item = self._queue.popleft()
            if isinstance(item, ProviderError):
                raise item
            return item
        return default

    async def generate(self, request: ImageGenerationRequest, reference_images: list[bytes]) -> bytes:
        self.calls.append((request, len(reference_images)))
        return self._next(f"fake-image:{request.prompt}".encode())

    async def edit(
        self, request: ImageEditRequest, base_image: bytes, mask: bytes | None = None
    ) -> bytes:
        self.edit_calls.append((request, mask is not None))
        return self._next(f"fake-edit:{request.instruction}".encode())
