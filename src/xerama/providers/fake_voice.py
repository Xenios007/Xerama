"""In-memory fake `VoiceProvider` for tests/local runs."""

from collections import deque

from xerama.providers.errors import ProviderError
from xerama.providers.voice import VoiceGenerationRequest, VoiceProviderCapabilities


class FakeVoiceProvider:
    def __init__(
        self,
        responses: list[bytes | ProviderError] | None = None,
        capabilities: VoiceProviderCapabilities | None = None,
        name: str = "fake_voice",
    ) -> None:
        self._queue: deque[bytes | ProviderError] = deque(responses or [])
        self._capabilities = capabilities or VoiceProviderCapabilities()
        self._name = name
        self.calls: list[VoiceGenerationRequest] = []

    def queue(self, item: bytes | ProviderError) -> None:
        self._queue.append(item)

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> VoiceProviderCapabilities:
        return self._capabilities

    async def synthesize(self, request: VoiceGenerationRequest) -> bytes:
        self.calls.append(request)
        if self._queue:
            item = self._queue.popleft()
            if isinstance(item, ProviderError):
                raise item
            return item
        return f"fake-voice:{request.text}".encode()
