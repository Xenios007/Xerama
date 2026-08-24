"""In-memory fake `LipSyncProvider` for tests/local runs."""

from collections import deque

from xerama.providers.errors import ProviderError
from xerama.providers.lip_sync import LipSyncProviderCapabilities, LipSyncRequest


class FakeLipSyncProvider:
    def __init__(
        self,
        responses: list[bytes | ProviderError] | None = None,
        capabilities: LipSyncProviderCapabilities | None = None,
        name: str = "fake_lip_sync",
    ) -> None:
        self._queue: deque[bytes | ProviderError] = deque(responses or [])
        self._capabilities = capabilities or LipSyncProviderCapabilities()
        self._name = name
        self.calls: list[LipSyncRequest] = []

    def queue(self, item: bytes | ProviderError) -> None:
        self._queue.append(item)

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> LipSyncProviderCapabilities:
        return self._capabilities

    async def sync(self, request: LipSyncRequest, video_bytes: bytes, audio_bytes: bytes) -> bytes:
        self.calls.append(request)
        if self._queue:
            item = self._queue.popleft()
            if isinstance(item, ProviderError):
                raise item
            return item
        return b"fake-lip-synced:" + video_bytes
