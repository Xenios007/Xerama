"""In-memory fake `MediaInspector` (MODULE-048) - same scripted-queue
pattern as every other fake provider. Defaults to a plausible PASS-shaped
probe (a fake render's placeholder bytes carry no real media metadata, so
there is nothing genuine to report) - queue a `MediaProbeResult` to script
a specific corruption/mismatch scenario.
"""

from collections import deque

from xerama.domain.export import MediaProbeResult


class FakeMediaInspector:
    def __init__(self, responses: list[MediaProbeResult] | None = None) -> None:
        self._queue: deque[MediaProbeResult] = deque(responses or [])
        self.calls: list[bytes] = []

    def queue(self, item: MediaProbeResult) -> None:
        self._queue.append(item)

    async def inspect(self, data: bytes) -> MediaProbeResult:
        self.calls.append(data)
        if self._queue:
            return self._queue.popleft()
        return MediaProbeResult(ok=True, has_video_stream=True, has_audio_stream=True)
