"""Creative brief - the user-supplied input to the story pipeline.

See docs/WORKFLOW.md Stage 0.
"""

from pydantic import BaseModel, Field

from xerama.domain.enums import ExecutionMode


class CreativeBrief(BaseModel):
    """Minimum input required to run the XER-001 story pipeline.

    Missing optional fields may be proposed by Xerama downstream, but the
    brief itself stays editable by the user rather than silently mutated.
    """

    genre: str
    premise: str = Field(
        default="",
        description="Optional starting idea. May be empty; Xerama proposes concepts either way.",
    )
    target_audience: str = "general"
    episode_count: int = Field(default=3, ge=1, le=100)
    episode_duration_seconds: int = Field(default=75, ge=15, le=600)
    tone: str = ""
    language: str = "en"
    content_restrictions: list[str] = Field(default_factory=list)
    mode: ExecutionMode = ExecutionMode.STANDARD
