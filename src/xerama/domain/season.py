"""Season & Reveal Engine contracts (XER-006).

The macro layer between the Series Bible and per-episode generation: acts,
the reveal ladder, mysteries, promises/payoffs, escalation, character-arc
milestones and the episode-to-act assignment. See docs/ROADMAP.md "Phase 1
... XER-006 - Season & Reveal Architecture" and docs/STORY_FORMULA.md
sections 3-4 (information gap, reveal/escalation ladder).

Audience knowledge is tracked separately from character knowledge (each
`RevealMilestone` records the audience's awareness before/after) because a
reveal to the audience and a reveal to a character are different narrative
events - see docs/STORY_FORMULA.md section 3.
"""

from pydantic import BaseModel, Field

from xerama.domain.enums import ArcStage, AwarenessStatus, CliffhangerType, ThreadStatus


class SeasonAct(BaseModel):
    act_number: int
    name: str
    start_episode: int
    end_episode: int
    objective: str
    description: str = ""


class Mystery(BaseModel):
    """A season-level question the audience is meant to be curious about."""

    id: str
    question: str
    introduced_episode: int
    resolution_episode: int | None = None
    status: ThreadStatus = ThreadStatus.OPEN


class Promise(BaseModel):
    """A setup that the season owes the audience a payoff for."""

    id: str
    description: str
    setup_episode: int
    payoff_episode: int | None = None
    status: ThreadStatus = ThreadStatus.OPEN


class RevealMilestone(BaseModel):
    """One planned reveal in the ladder. See docs/STORY_FORMULA.md section 4."""

    id: str
    description: str
    planned_episode: int
    mystery_id: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    audience_knowledge_before: AwarenessStatus = AwarenessStatus.UNKNOWN
    audience_knowledge_after: AwarenessStatus = AwarenessStatus.KNOWS


class EscalationMilestone(BaseModel):
    episode_number: int
    escalation_level: float = Field(ge=0, le=10)
    description: str = ""


class CharacterArcMilestone(BaseModel):
    character_id: str
    episode_number: int
    milestone: str
    arc_stage: ArcStage = ArcStage.SETUP


class EpisodeAssignment(BaseModel):
    """Maps one requested episode number onto the season structure."""

    episode_number: int
    act_number: int
    objective: str
    reveals: list[str] = Field(default_factory=list)
    promises_setup: list[str] = Field(default_factory=list)
    promises_paid_off: list[str] = Field(default_factory=list)
    escalation_level: float = Field(ge=0, le=10)
    character_milestones: list[str] = Field(default_factory=list)
    cliffhanger_type: CliffhangerType | None = None


class SeasonPlan(BaseModel):
    """The full season/reveal map for a requested episode count."""

    series_title: str
    episode_count: int
    acts: list[SeasonAct]
    mysteries: list[Mystery] = Field(default_factory=list)
    promises: list[Promise] = Field(default_factory=list)
    reveals: list[RevealMilestone] = Field(default_factory=list)
    escalation_milestones: list[EscalationMilestone] = Field(default_factory=list)
    character_arc_milestones: list[CharacterArcMilestone] = Field(default_factory=list)
    episode_assignments: list[EpisodeAssignment]
