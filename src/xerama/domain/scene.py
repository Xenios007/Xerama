"""Production scene/shot contracts (Director Engine). See docs/ARCHITECTURE.md
section 9 and docs/DATA_MODEL.md Scene/Shot.

No media generation happens in XER-001. This schema exists so later stages
(image/video generation) can consume it without a redesign - see ADR-016.
"""

from pydantic import BaseModel, Field

from xerama.domain.enums import AudioMode, BlockingDepth, ScreenPosition


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
    """Temporal beat within a generated shot. See ADR-016 and MODULE-033
    (Character Motion/Performance) - `character_id`/`pose`/`expression`/
    `gaze`/`camera_note` turn this from a single unbounded prose sentence
    into structured performance data. All optional/defaulted so existing
    beats (`description` only) keep working unchanged."""

    start_seconds: float
    end_seconds: float
    description: str
    # Which character this beat is about - links performance to speaker,
    # required for `DirectorValidator.check_motion_plan`'s overlap check.
    character_id: str | None = None
    pose: str = ""
    expression: str = ""
    gaze: str = ""
    camera_note: str = ""


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


class CharacterBlock(BaseModel):
    """Where one character sits in the frame for a shot - see MODULE-022
    Scene Blocking. Lightweight left/center/right + depth, not real
    coordinates; `facing`/`occluded_by` stay free text/id-list so this
    never needs a full 3D engine to be useful."""

    character_id: str
    position: ScreenPosition = ScreenPosition.CENTER
    depth: BlockingDepth = BlockingDepth.MIDGROUND
    facing: str = ""
    visible: bool = True
    speaking: bool = False
    reacting: bool = False
    occluded_by: list[str] = Field(default_factory=list)


class MovementBeat(BaseModel):
    """A character's position change within a shot - see MODULE-022."""

    start_seconds: float
    end_seconds: float
    character_id: str
    description: str = ""
    from_position: ScreenPosition | None = None
    to_position: ScreenPosition | None = None


class SceneBlocking(BaseModel):
    """Structured actor placement/movement for one shot - see MODULE-022.
    Additive alongside `Shot.blocking` (free text); this is what
    `DirectorValidator.check_scene_blocking` actually validates."""

    characters: list[CharacterBlock] = Field(default_factory=list)
    movement_beats: list[MovementBeat] = Field(default_factory=list)
    # The established movement/eyeline axis for this shot (e.g.
    # "left_to_right") - checked for consistency across a continuity_group
    # so "preserve screen direction across connected shots" is verifiable.
    screen_direction: str = ""


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
    # Deliberately free text, not a coordinate/spatial system - "avoid
    # overengineering spatial blocking V1". `blocking_plan` (MODULE-022)
    # adds optional lightweight structure alongside this prose without
    # replacing it.
    blocking: str = ""
    blocking_plan: SceneBlocking | None = None
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
