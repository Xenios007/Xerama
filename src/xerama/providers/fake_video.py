"""In-memory fake `VideoProvider` for tests/local runs - same scripted-queue
pattern as `FakeLLMProvider`/`FakeImageProvider`."""

from collections import deque

from xerama.providers.errors import ProviderError
from xerama.providers.video import VideoGenerationRequest, VideoProviderCapabilities


class FakeVideoProvider:
    def __init__(
        self,
        responses: list[bytes | ProviderError] | None = None,
        capabilities: VideoProviderCapabilities | None = None,
        name: str = "fake_video",
    ) -> None:
        self._queue: deque[bytes | ProviderError] = deque(responses or [])
        self._capabilities = capabilities or VideoProviderCapabilities()
        self._name = name
        self.calls: list[VideoGenerationRequest] = []

    def queue(self, item: bytes | ProviderError) -> None:
        self._queue.append(item)

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> VideoProviderCapabilities:
        return self._capabilities

    async def generate(
        self,
        request: VideoGenerationRequest,
        reference_images: list[bytes],
        first_frame: bytes | None = None,
        last_frame: bytes | None = None,
    ) -> bytes:
        self.calls.append(request)
        if self._queue:
            item = self._queue.popleft()
            if isinstance(item, ProviderError):
                raise item
            return item
        return f"fake-video:{request.prompt}".encode()
