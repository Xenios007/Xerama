"""Lip-sync / performance-transfer provider contract (Module 07).

See research/PRODUCTION_STACK_2026.md "Lip sync / performance transfer" -
kept behind an adapter since public AI-drama systems already route among
multiple lip-sync providers.
"""

from typing import Protocol

from pydantic import BaseModel, Field


class LipSyncProviderCapabilities(BaseModel):
    max_duration_seconds: float = 15.0
    supported_aspects: list[str] = Field(default_factory=lambda: ["9:16"])
    priority: int = 0
    estimated_cost_usd: float = 0.0


class LipSyncRequest(BaseModel):
    aspect_ratio: str = "9:16"
    duration_seconds: float = 5.0


class LipSyncProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def capabilities(self) -> LipSyncProviderCapabilities: ...

    async def sync(self, request: LipSyncRequest, video_bytes: bytes, audio_bytes: bytes) -> bytes: ...
