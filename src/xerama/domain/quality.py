"""Quality-control and story-scoring contracts.

See docs/STORY_FORMULA.md section 6, docs/JSON_CONTRACTS.md Quality Score,
and ADR-018 (pass/warn/block, not one opaque score).
"""

from pydantic import BaseModel, Field

from xerama.domain.enums import QCStatus


class QualityScore(BaseModel):
    """See docs/JSON_CONTRACTS.md Quality Score. All dimensions are 0-10."""

    hook: float = Field(ge=0, le=10)
    conflict: float = Field(ge=0, le=10)
    emotional_intensity: float = Field(ge=0, le=10)
    information_gap: float = Field(ge=0, le=10)
    reversal: float = Field(ge=0, le=10)
    cliffhanger: float = Field(ge=0, le=10)
    character_consistency: float = Field(ge=0, le=10)
    continuity: float = Field(ge=0, le=10)
    serial_progress: float = Field(ge=0, le=10)
    originality: float = Field(ge=0, le=10)
    production_feasibility: float = Field(ge=0, le=10)
    repetition_risk: float = Field(ge=0, le=10)
    overall: float = Field(ge=0, le=10)
    blocking_issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class QCResult(BaseModel):
    """Multi-dimensional quality gate verdict. See ADR-018."""

    gate: str
    status: QCStatus
    score: float = Field(ge=0, le=10)
    reasons: list[str] = Field(default_factory=list)
    repair_recommendation: str = ""
