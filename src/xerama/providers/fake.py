"""In-memory fake `LLMProvider` for tests and local pipeline runs without a
paid API call. Implements the same Protocol as `OpenRouterProvider`.
"""

from collections import deque

from xerama.providers.errors import ProviderError
from xerama.providers.llm import LLMRequest, LLMResponse


class FakeLLMProvider:
    """Returns pre-scripted responses in call order.

    Each queued item is either a JSON string (becomes the response content)
    or a `ProviderError` instance to raise instead. All requests are
    recorded in `.calls` for assertions.
    """

    def __init__(self, responses: list[str | ProviderError] | None = None) -> None:
        self._queue: deque[str | ProviderError] = deque(responses or [])
        self.calls: list[LLMRequest] = []

    def queue(self, item: str | ProviderError) -> None:
        self._queue.append(item)

    @property
    def name(self) -> str:
        return "fake"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        if not self._queue:
            raise AssertionError("FakeLLMProvider queue exhausted - add more scripted responses")
        item = self._queue.popleft()
        if isinstance(item, ProviderError):
            raise item
        return LLMResponse(
            content=item,
            latency_ms=1.0,
            model=request.model,
            finish_reason="stop",
            prompt_tokens=10,
            completion_tokens=10,
        )
