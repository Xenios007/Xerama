"""In-memory fake `MediaQCProvider` (MODULE-044) - same scripted-queue
pattern as every other fake provider (`fake_image.py`, `fake_video.py`,
`fake_voice.py`, `fake_lip_sync.py`). Defaults to a comfortable PASS so
accepting takes in tests/local runs behaves exactly as it did before this
module existed; queue a `QCResult` (or a `ProviderError`) to script a
WARN/BLOCK/failure for a specific dimension.
"""

from collections import deque

from xerama.domain.asset import Asset
from xerama.domain.enums import MediaQCDimension, QCStatus
from xerama.domain.quality import QCResult
from xerama.providers.errors import ProviderError
from xerama.providers.media_qc import MediaQCContext


class FakeMediaQCProvider:
    def __init__(self, responses: list[QCResult | ProviderError] | None = None) -> None:
        self._queue: deque[QCResult | ProviderError] = deque(responses or [])
        self.calls: list[tuple[MediaQCDimension, str]] = []

    def queue(self, item: QCResult | ProviderError) -> None:
        self._queue.append(item)

    async def score(
        self,
        dimension: MediaQCDimension,
        candidate_asset: Asset,
        candidate_bytes: bytes,
        reference_bytes: list[bytes],
        context: MediaQCContext,
    ) -> QCResult:
        self.calls.append((dimension, candidate_asset.id))
        if self._queue:
            item = self._queue.popleft()
            if isinstance(item, ProviderError):
                raise item
            return item
        return QCResult(gate=dimension.value, status=QCStatus.PASS, score=8.0, reasons=[])
