"""In-process rate limiting / concurrency / duplicate-request suppression
(MODULE-068).

Deliberately in-memory, not DB-backed - this guards against runaway
*request volume* within one running process, the same operational
category as `ProviderHealthTracker` (ADR-011), not durable state that
needs to survive a restart or be shared across processes. A future
multi-worker hosted deployment would swap this for a shared store
(Redis token bucket, etc.) behind the same interface; Trial 01's "a
simple ... local worker is acceptable" pragmatism (docs/ARCHITECTURE.md
section 14) applies here too.

One `RateLimiter` instance lives for the process lifetime (see
`app.state.rate_limiter`, built once in `app.py`'s `lifespan`) and is
shared across every request - state must key everything by `project_id`
so one project's traffic never throttles another's.
"""

import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class RateLimitExceededError(RuntimeError):
    def __init__(self, message: str, retry_after_seconds: float) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class ConcurrencyLimitExceededError(RuntimeError):
    pass


class DuplicateRequestError(RuntimeError):
    pass


class RateLimiter:
    def __init__(
        self,
        requests_per_window: int,
        window_seconds: float,
        max_concurrent_per_project: int,
    ) -> None:
        self._requests_per_window = requests_per_window
        self._window_seconds = window_seconds
        self._max_concurrent = max_concurrent_per_project
        self._request_times: dict[str, deque[float]] = defaultdict(deque)
        self._in_flight_count: dict[str, int] = defaultdict(int)
        self._in_flight_keys: set[str] = set()

    def check_request_rate(self, project_id: str, now: float | None = None) -> None:
        """Sliding-window request-count check. Raises
        `RateLimitExceededError` (with `retry_after_seconds`) if this
        project has already made `requests_per_window` requests within
        the trailing `window_seconds`; otherwise records this request."""
        now = now if now is not None else time.monotonic()
        window = self._request_times[project_id]
        while window and now - window[0] > self._window_seconds:
            window.popleft()
        if len(window) >= self._requests_per_window:
            retry_after = self._window_seconds - (now - window[0])
            raise RateLimitExceededError(
                f"request rate limit exceeded for project {project_id!r} "
                f"({self._requests_per_window} requests per {self._window_seconds:.0f}s)",
                retry_after_seconds=max(retry_after, 0.0),
            )
        window.append(now)

    @asynccontextmanager
    async def acquire_concurrency_slot(self, project_id: str) -> AsyncIterator[None]:
        """Raises `ConcurrencyLimitExceededError` immediately (never
        blocks/queues - a queued generation request is still "runaway
        expensive work" from the caller's perspective) if this project
        already has `max_concurrent_per_project` generations in flight."""
        if self._in_flight_count[project_id] >= self._max_concurrent:
            raise ConcurrencyLimitExceededError(
                f"concurrency limit exceeded for project {project_id!r} "
                f"(max {self._max_concurrent} in-flight generations)"
            )
        self._in_flight_count[project_id] += 1
        try:
            yield
        finally:
            self._in_flight_count[project_id] -= 1

    @asynccontextmanager
    async def suppress_duplicate(self, key: str) -> AsyncIterator[None]:
        """Raises `DuplicateRequestError` if a generation request with
        the exact same `key` (typically `f"{project_id}:{resource}:{id}"`
        - e.g. the same storyboard's keyframe) is already in flight -
        "duplicate-generation suppression": a double-click or a retried
        client request must not pay for the same provider call twice."""
        if key in self._in_flight_keys:
            raise DuplicateRequestError(f"an identical generation request is already in flight: {key!r}")
        self._in_flight_keys.add(key)
        try:
            yield
        finally:
            self._in_flight_keys.discard(key)
