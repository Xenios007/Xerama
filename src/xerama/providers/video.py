"""Video provider contract (Module 07).

See research/PRODUCTION_STACK_2026.md "Video provider contract". Shots
already declare what they need from a video provider via
`domain.scene.ProviderRequirements` (Module 03) - "Declared here at the
shot level so the Module 07 router can filter eligible providers without
the Director knowing vendor names." `matches_requirements` is that filter.
"""

from typing import Protocol

from pydantic import BaseModel, Field

from xerama.domain.scene import ProviderRequirements


class VideoProviderCapabilities(BaseModel):
    text_to_video: bool = True
    image_to_video: bool = True
    first_frame: bool = True
    last_frame: bool = False
    subject_reference: bool = True
    native_audio: bool = False
    max_duration_seconds: float = 10.0
    supported_aspects: list[str] = Field(default_factory=lambda: ["9:16"])
    supported_resolutions: list[str] = Field(default_factory=lambda: ["1080x1920"])
    priority: int = 0
    estimated_cost_usd: float = 0.0


class VideoGenerationRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    aspect_ratio: str = "9:16"
    duration_seconds: float = 5.0


class VideoProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def capabilities(self) -> VideoProviderCapabilities: ...

    async def generate(
        self,
        request: VideoGenerationRequest,
        reference_images: list[bytes],
        first_frame: bytes | None = None,
        last_frame: bytes | None = None,
    ) -> bytes: ...


def matches_requirements(
    capabilities: VideoProviderCapabilities,
    requirements: ProviderRequirements,
    aspect_ratio: str = "9:16",
    duration_seconds: float = 0.0,
) -> bool:
    """The eligibility filter a `MediaProviderRouter[VideoProvider]` should
    apply before ranking/attempting a provider - "reject an incompatible
    provider before spending a generation request"."""
    if aspect_ratio not in capabilities.supported_aspects:
        return False
    if duration_seconds and duration_seconds > capabilities.max_duration_seconds:
        return False
    if requirements.text_to_video and not capabilities.text_to_video:
        return False
    if requirements.image_to_video and not capabilities.image_to_video:
        return False
    if requirements.first_frame_required and not capabilities.first_frame:
        return False
    if requirements.last_frame_required and not capabilities.last_frame:
        return False
    if requirements.subject_reference_required and not capabilities.subject_reference:
        return False
    if requirements.native_audio_required and not capabilities.native_audio:
        return False
    return True
