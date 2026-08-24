"""Episode beat sheet and script contracts. See docs/JSON_CONTRACTS.md."""

from pydantic import BaseModel, Field

from xerama.domain.enums import CliffhangerType


class CharacterInformationGain(BaseModel):
    character_id: str
    fact_id: str


class Cliffhanger(BaseModel):
    type: CliffhangerType
    event: str


class EpisodeOutline(BaseModel):
    """Beat sheet for one episode. See docs/JSON_CONTRACTS.md Episode Beat Sheet."""

    episode_number: int
    title: str = ""
    objective: str
    opening_hook: str
    stakes: str
    conflict: str
    escalation: list[str] = Field(default_factory=list)
    turn: str
    reveal: str
    audience_information_gain: list[str] = Field(default_factory=list)
    character_information_gain: list[CharacterInformationGain] = Field(default_factory=list)
    cliffhanger: Cliffhanger
    canon_changes: list[str] = Field(default_factory=list)
    duration_target_seconds: int


class EpisodeOutlineSet(BaseModel):
    """AI generation output for the episode-outline stage (multiple episodes)."""

    outlines: list[EpisodeOutline]


class DialogueLine(BaseModel):
    character_id: str
    character_name: str
    line: str


class ScriptScene(BaseModel):
    """Prose-level scene as written by the episode writer.

    This is distinct from the production `Scene` in domain/scene.py, which
    is the shot-level breakdown produced by the Director/shot-planner stage.
    """

    scene_number: int
    location: str
    time_of_day: str = ""
    characters: list[str] = Field(default_factory=list)
    action: str
    dialogue: list[DialogueLine] = Field(default_factory=list)


class EpisodeScript(BaseModel):
    """Full written episode. See docs/WORKFLOW.md Stage 5."""

    episode_number: int
    title: str
    scenes: list[ScriptScene]
    estimated_duration_seconds: float
