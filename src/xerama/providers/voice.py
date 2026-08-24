"""Voice/TTS provider contract (Module 07).

See research/PRODUCTION_STACK_2026.md "Voice" - a character's voice is
stored as an asset independent of the video provider (voice provider,
voice id, language, style, rights metadata), so the same character
survives a video-provider swap.
"""

from typing import Protocol

from pydantic import BaseModel, Field


class VoiceProviderCapabilities(BaseModel):
    supports_voice_cloning: bool = False
    supports_ssml: bool = False
    languages: list[str] = Field(default_factory=lambda: ["en"])
    max_characters: int = 5000
    priority: int = 0
    estimated_cost_usd: float = 0.0


class VoiceGenerationRequest(BaseModel):
    text: str
    voice_id: str = ""
    language: str = "en"


class VoiceProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def capabilities(self) -> VoiceProviderCapabilities: ...

    async def synthesize(self, request: VoiceGenerationRequest) -> bytes: ...
