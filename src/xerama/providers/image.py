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


class ImageEditRequest(BaseModel):
    """See MODULE-030 - repair a failed still without a full regenerate.
    `instruction` describes the change (e.g. "fix the left hand"); `mask`
    bytes are optional even for a `supports_mask` provider (a global edit
    without a mask is still a valid edit request)."""

    instruction: str
    negative_prompt: str = ""
    aspect_ratio: str = "9:16"


class ImageProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def capabilities(self) -> ImageProviderCapabilities: ...

    async def generate(self, request: ImageGenerationRequest, reference_images: list[bytes]) -> bytes: ...

    async def edit(
        self, request: ImageEditRequest, base_image: bytes, mask: bytes | None = None
    ) -> bytes:
        """Only ever called on a provider whose `capabilities.supports_edit`
        is `True` - the `MediaProviderRouter`'s capability filter (Module
        07) keeps providers without real edit support out of the routing
        pool before this is invoked."""
        ...
