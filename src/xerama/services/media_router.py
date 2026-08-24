"""Generic media-provider router (Module 07).

Generalizes provider routing beyond the single OpenRouter LLM provider
(`pipeline/ai_gateway.py`, left untouched - "Preserve current OpenRouter
behavior") to any media provider type (image, video, voice, lip-sync, ...).

A caller asks for a capability, not a vendor: capability filter -> health
filter -> priority order -> attempt -> on failure, record the reason and
try the next eligible provider. Reuses the existing `ProviderError`/
`ProviderHealthTracker` abstractions (ADR-011) instead of building a
second health/error system - see
research/PRODUCTION_STACK_2026.md "Provider health and fallback":

    request -> capability filter -> health filter -> cost/quality ranking
    -> provider A (fail -> provider B (fail -> provider C))

Works over any provider type that exposes `.name: str` and
`.capabilities` with an int `.priority` - image/video/voice/lip-sync
providers all satisfy this despite having entirely different capability
shapes, so this router is written once rather than per media type.
"""

from collections.abc import Awaitable, Callable
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel

from xerama.providers.errors import ProviderError
from xerama.providers.health import ProviderHealthTracker


class _HasPriority(Protocol):
    priority: int


class _RoutableProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def capabilities(self) -> _HasPriority: ...


P = TypeVar("P", bound=_RoutableProvider)


class RoutingAttempt(BaseModel):
    provider_name: str
    outcome: str  # "selected" | "incompatible" | "unhealthy" | "failed"
    detail: str = ""


class NoEligibleProviderError(RuntimeError):
    """No registered provider was both capability-compatible and healthy,
    or every eligible provider's attempt failed."""

    def __init__(self, attempts: list[RoutingAttempt]) -> None:
        self.attempts = attempts
        summary = "; ".join(f"{a.provider_name}={a.outcome}" for a in attempts) or "no providers registered"
        super().__init__(f"no eligible media provider available: {summary}")


class MediaProviderRouter(Generic[P]):
    def __init__(self, providers: list[P], health: ProviderHealthTracker | None = None) -> None:
        # Deterministic policy ordering: higher `capabilities.priority`
        # is tried first. Ties keep registration order (Python sort is
        # stable) so ordering never depends on dict/set iteration.
        self._providers = sorted(providers, key=lambda p: p.capabilities.priority, reverse=True)
        self._health = health or ProviderHealthTracker()

    @property
    def providers(self) -> list[P]:
        return list(self._providers)

    async def generate(
        self,
        is_compatible: Callable[[P], bool],
        call: Callable[[P], Awaitable[bytes]],
    ) -> tuple[P, bytes, list[RoutingAttempt]]:
        attempts: list[RoutingAttempt] = []
        for provider in self._providers:
            if not is_compatible(provider):
                attempts.append(RoutingAttempt(provider_name=provider.name, outcome="incompatible"))
                continue
            if not self._health.is_healthy(provider.name, "default"):
                attempts.append(RoutingAttempt(provider_name=provider.name, outcome="unhealthy"))
                continue
            try:
                data = await call(provider)
            except ProviderError as exc:
                self._health.record_failure(provider.name, "default", exc.kind)
                attempts.append(
                    RoutingAttempt(provider_name=provider.name, outcome="failed", detail=exc.message)
                )
                continue
            self._health.record_success(provider.name, "default")
            attempts.append(RoutingAttempt(provider_name=provider.name, outcome="selected"))
            return provider, data, attempts
        raise NoEligibleProviderError(attempts)
