"""Provider-neutral intermediate generation request (Module 03).

The output of the Prompt Compiler: shot intent + Character DNA/references +
location/props + continuity frame + negative constraints, combined into one
structured request. No vendor-specific syntax (Runway/Kling/Veo/etc.)
belongs here - a provider adapter (Module 07+) translates this into a
vendor payload. See research/WIND_COMIC_DEEP_DIVE.md section 23 (prompt
compilation should be centralized).
"""

from pydantic import BaseModel, Field

from xerama.domain.enums import AudioMode
from xerama.domain.scene import Camera, ProviderRequirements, Visual


class CompiledReferences(BaseModel):
    character_asset_ids: list[str] = Field(default_factory=list)
    style_asset_id: str | None = None
    location_asset_id: str | None = None
    prop_asset_ids: list[str] = Field(default_factory=list)
    continuity_frame_asset_id: str | None = None


class ShotGenerationRequest(BaseModel):
    """Media-ready structured shot - what a future image/video provider
    adapter consumes. Deterministically compiled, never itself an LLM call."""

    shot_number: int
    scene_number: int
    prompt: str
    negative_prompt: str = ""
    character_dna: list[str] = Field(default_factory=list)
    style_dna: str = ""
    duration_seconds: float
    aspect_ratio: str = "9:16"
    camera: Camera
    visual: Visual
    blocking: str = ""
    audio_mode: AudioMode
    references: CompiledReferences
    provider_requirements: ProviderRequirements
    continuity_group: str | None = None
