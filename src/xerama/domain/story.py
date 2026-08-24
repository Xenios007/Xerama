"""Concept, judge and series bible contracts. See docs/JSON_CONTRACTS.md."""

from pydantic import BaseModel, Field

from xerama.domain.enums import JudgeDecision


class Protagonist(BaseModel):
    name: str
    role: str
    desire: str
    flaw: str


class ConceptCandidate(BaseModel):
    """One independently generated microdrama concept. See JSON_CONTRACTS.md."""

    title: str
    genre: list[str]
    logline: str
    premise: str
    protagonist: Protagonist
    antagonistic_force: str
    central_conflict: str
    central_secret: str
    emotional_engine: str
    opening_hook: str
    serial_engine: str
    major_reversals: list[str] = Field(default_factory=list)
    ending_direction: str
    production_notes: list[str] = Field(default_factory=list)


class CandidateScore(BaseModel):
    score: float = Field(ge=0, le=10)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class JudgeCriteria(BaseModel):
    """See docs/STORY_FORMULA.md section 6."""

    hook: float = Field(ge=0, le=10)
    emotional_intensity: float = Field(ge=0, le=10)
    conflict: float = Field(ge=0, le=10)
    originality: float = Field(ge=0, le=10)
    serial_potential: float = Field(ge=0, le=10)
    reversal_potential: float = Field(ge=0, le=10)
    cliffhanger_potential: float = Field(ge=0, le=10)
    production_feasibility: float = Field(ge=0, le=10)
    character_potential: float = Field(ge=0, le=10)


class MergeInstructions(BaseModel):
    take_from_a: list[str] = Field(default_factory=list)
    take_from_b: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)


class JudgeResult(BaseModel):
    """AI judge output. Decision is A, B or MERGE. See docs/DECISIONS.md ADR-003."""

    decision: JudgeDecision
    candidate_a: CandidateScore
    candidate_b: CandidateScore
    criteria: JudgeCriteria
    reason: str
    merge_instructions: MergeInstructions = Field(default_factory=MergeInstructions)


class SeriesBible(BaseModel):
    """Approved creative truth for a series.

    Reconciles a documentation inconsistency found during implementation:
    docs/JSON_CONTRACTS.md's SeriesBible JSON schema and docs/DATA_MODEL.md's
    prose field list for "Series Bible" name different, only partially
    overlapping fields (e.g. DATA_MODEL.md's "premise", "protagonist
    objective", "primary opposition" and "prohibited contradictions" are
    absent from the JSON_CONTRACTS.md schema). Per README/DECISIONS.md
    conflict-resolution guidance this is not architecturally blocking, so
    this schema is the union of both rather than a strict pick of one -
    logged in docs/IMPLEMENTATION_STATUS.md.
    """

    title: str
    logline: str
    genres: list[str]
    tone: list[str] = Field(default_factory=list)
    target_audience: str
    episode_count: int
    episode_duration_seconds: int
    premise: str = ""
    themes: list[str] = Field(default_factory=list)
    emotional_engine: str
    central_dramatic_question: str
    protagonist_objective: str = ""
    primary_opposition: str = ""
    world_rules: list[str] = Field(default_factory=list)
    central_secret: str
    ending_target: str
    prohibited_contradictions: list[str] = Field(default_factory=list)
    locked_facts: list[str] = Field(default_factory=list)
