"""Canonical series state contracts. See docs/DATA_MODEL.md and ADR-005/ADR-006.

LLM chat history is not series memory. `CanonSnapshot` is the compact,
explicit context supplied to models; `CanonEvent` is a proposed or committed
state mutation. Model output becomes canon only after validation - see the
Canon Commit Rule in docs/DATA_MODEL.md.
"""

from pydantic import BaseModel, Field

from xerama.domain.enums import CanonChangeType


class CanonEvent(BaseModel):
    """A single proposed/committed canonical state change."""

    change_type: CanonChangeType
    episode_number: int
    description: str
    payload: dict = Field(default_factory=dict)
    committed: bool = False


class CanonSnapshot(BaseModel):
    """Compact canonical context handed to a model for one generation task.

    Deliberately does not include full episode prose - only the state a
    given stage needs, per docs/ARCHITECTURE.md "Provider independence" /
    "Canonical state over prompt memory".
    """

    series_title: str
    locked_facts: list[str] = Field(default_factory=list)
    character_summaries: list[str] = Field(default_factory=list)
    unresolved_hooks: list[str] = Field(default_factory=list)
    prior_events: list[str] = Field(default_factory=list)
    recap: str = ""
