"""Multimodal QC vision-provider contract (MODULE-044).

Generalizes `providers/identity_qc.py`'s deferred `IdentityQCProvider` (see
that module's docstring - "defers multimodal implementation to Module 11",
which is this module) into one Protocol covering every QC dimension that
genuinely needs a vision-capable model to score: identity, style,
continuity, composition, motion. `MediaQCDimension.MEDIA_HEALTH` and
`.DIALOGUE_AUDIO` need no model at all - see `pipeline/media_qc_checks.py`.

No real (paid/free) implementation exists yet - same "contract + fake now,
real adapter later" pattern as every other media provider in this codebase
(Modules 06/07/08/09/10). A real implementation only has to satisfy this
one interface for every vision-based dimension, never a new parallel one.
"""

from typing import Protocol

from pydantic import BaseModel, Field

from xerama.domain.asset import Asset
from xerama.domain.enums import MediaQCDimension
from xerama.domain.quality import QCResult


class MediaQCContext(BaseModel):
    """Optional comparison/expectation data a check may use - not every
    field applies to every dimension. `reference_asset_ids` feeds
    IDENTITY/STYLE/CONTINUITY (e.g. a character reference pack asset, a
    Style Bible anchor asset, a previous shot's extracted last frame);
    `expected_duration_seconds`/`expected_aspect_ratio` feed the
    deterministic MEDIA_HEALTH/DIALOGUE_AUDIO checks."""

    reference_asset_ids: list[str] = Field(default_factory=list)
    shot_description: str = ""
    style_dna: str = ""
    expected_duration_seconds: float | None = None
    expected_aspect_ratio: str | None = None


class MediaQCProvider(Protocol):
    """Scores one candidate asset on one QC dimension against optional
    reference bytes/context. See ADR-018 - always pass/warn/block plus
    reasons and a repair recommendation, never one opaque number."""

    async def score(
        self,
        dimension: MediaQCDimension,
        candidate_asset: Asset,
        candidate_bytes: bytes,
        reference_bytes: list[bytes],
        context: MediaQCContext,
    ) -> QCResult: ...
