"""Image provider contract (Module 06).

See research/PRODUCTION_STACK_2026.md "Provider contract": image adapters
expose capability metadata so an incompatible provider can be rejected
*before* spending a generation request, not after a failed call.
"""

from typing import Protocol

from pydantic import BaseModel, Field


class ImageProviderCapabilities(BaseModel):
    supports_reference_images: bool = True
    max_reference_images: int = 4
    supports_edit: bool = False
    supports_mask: bool = False
    supported_aspects: list[str] = Field(default_factory=lambda: ["9:16"])
    priority: int = 0
    estimated_cost_usd: float = 0.0


class ImageGenerationRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    aspect_ratio: str = "9:16"


class ImageProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def capabilities(self) -> ImageProviderCapabilities: ...

    async def generate(self, request: ImageGenerationRequest, reference_images: list[bytes]) -> bytes: ...
