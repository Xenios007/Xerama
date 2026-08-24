"""Production scene/shot contracts (Director Engine). See docs/ARCHITECTURE.md
section 9 and docs/DATA_MODEL.md Scene/Shot.

No media generation happens in XER-001. This schema exists so later stages
(image/video generation) can consume it without a redesign - see ADR-016.
"""

from pydantic import BaseModel, Field

from xerama.domain.enums import AudioMode


class Camera(BaseModel):
    shot_size: str = ""
    angle: str = ""
    lens: str = ""
    movement: str = ""


class Visual(BaseModel):
    composition: str = ""
    lighting: str = ""
    emotion: str = ""


class ShotReferences(BaseModel):
    """Production anchors a shot should compile from. See ADR-014."""

    character_asset_ids: list[str] = Field(default_factory=list)
    style_asset_id: str | None = None
    location_asset_id: str | None = None
    prop_asset_ids: list[str] = Field(default_factory=list)
    previous_continuity_frame_asset_id: str | None = None


class MicroBeat(BaseModel):
    """Temporal beat within a generated shot. See ADR-016."""

    start_seconds: float
    end_seconds: float
    description: str


class ProviderRequirements(BaseModel):
    """Capabilities this shot needs from whichever video provider ends up
    generating it - see docs/ARCHITECTURE.md section 6 (Provider Registry).
    Declared here at the shot level so the Module 07 router can filter
    eligible providers without the Director knowing vendor names.
    """

    text_to_video: bool = False
    image_to_video: bool = True
    first_frame_required: bool = True
    last_frame_required: bool = False
    subject_reference_required: bool = True
    native_audio_required: bool = False


class Shot(BaseModel):
    """See docs/ARCHITECTURE.md section 9 (Shot Contract)."""

    shot_number: int
    scene_number: int
    narrative_function: str = ""
    character_ids: list[str] = Field(default_factory=list)
    dialogue: str = ""
    action: str = ""
    duration_seconds: float = Field(gt=0)
    camera: Camera = Field(default_factory=Camera)
    visual: Visual = Field(default_factory=Visual)
    # Deliberately free text, not a coordinate/spatial system - see
    # modules/03_DIRECTOR_PROMPT_COMPILER.md "Avoid overengineering spatial
    # blocking V1".
    blocking: str = ""
    references: ShotReferences = Field(default_factory=ShotReferences)
    micro_beats: list[MicroBeat] = Field(default_factory=list)
    audio_mode: AudioMode = AudioMode.NATIVE
    continuity_requirements: list[str] = Field(default_factory=list)
    # Shots sharing a continuity_group are adjacent and should be generated
    # sequentially so Shot N's actual last frame can anchor Shot N+1 - see
    # ADR-017. None means this shot can be generated independently/in
    # parallel with any other shot.
    continuity_group: str | None = None
    provider_requirements: ProviderRequirements = Field(default_factory=ProviderRequirements)
    generation_status: str = "planned"


class Scene(BaseModel):
    """See docs/DATA_MODEL.md Scene."""

    scene_number: int
    location: str
    time_of_day: str = ""
    characters: list[str] = Field(default_factory=list)
    objective: str = ""
    conflict: str = ""
    outcome: str = ""
    shots: list[Shot] = Field(default_factory=list)


class EpisodeShotPlan(BaseModel):
    """AI generation output for the scene/shot-planning stage."""

    episode_number: int
    scenes: list[Scene]
