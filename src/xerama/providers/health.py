"""Minimal provider health / circuit breaker. See ADR-011.

Kept deliberately simple for Trial 01: an in-memory failure counter per
(provider, model) with a cool-down window. A broken provider/model stops
being offered as healthy for a short period instead of consuming every job
retry.
"""

import time

from xerama.domain.enums import ProviderErrorKind
from xerama.providers.errors import RETRIABLE_KINDS

_FAILURE_THRESHOLD = 3
_COOL_DOWN_SECONDS = 60.0


class ProviderHealthTracker:
    def __init__(self) -> None:
        self._failures: dict[str, int] = {}
        self._open_until: dict[str, float] = {}

    def _key(self, provider: str, model: str) -> str:
        return f"{provider}:{model}"

    def record_success(self, provider: str, model: str) -> None:
        key = self._key(provider, model)
        self._failures.pop(key, None)
        self._open_until.pop(key, None)

    def record_failure(self, provider: str, model: str, kind: ProviderErrorKind) -> None:
        if kind not in RETRIABLE_KINDS and kind != ProviderErrorKind.UNKNOWN:
            # Non-retriable errors (auth, quota, invalid request) trip the
            # breaker immediately - retrying the same call will not help.
            self._open_until[self._key(provider, model)] = time.monotonic() + _COOL_DOWN_SECONDS
            return
        key = self._key(provider, model)
        self._failures[key] = self._failures.get(key, 0) + 1
        if self._failures[key] >= _FAILURE_THRESHOLD:
            self._open_until[key] = time.monotonic() + _COOL_DOWN_SECONDS

    def is_healthy(self, provider: str, model: str) -> bool:
        key = self._key(provider, model)
        open_until = self._open_until.get(key)
        if open_until is None:
            return True
        if time.monotonic() >= open_until:
            self._open_until.pop(key, None)
            self._failures.pop(key, None)
            return True
        return False
