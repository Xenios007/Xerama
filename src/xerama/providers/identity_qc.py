"""Identity-QC contract (Module 05 "QC hooks").

Defines the interface and thresholds a future multimodal identity scorer
must satisfy. No implementation lives here - Module 05 explicitly defers
"multimodal implementation to Module 11" (face/likeness comparison requires
an actual vision model, which is out of scope for the provider-neutral
identity/casting layer built here).

See research/CHARACTER_CONTINUITY_PLAYBOOK.md "Continuity scoring" and
"Automated identity retry".
"""

from typing import Protocol

from xerama.domain.asset import Asset
from xerama.domain.character import Character
from xerama.domain.quality import QCResult

IDENTITY_QC_GATE = "identity_consistency"

# Placeholder thresholds pending Module 11's real multimodal scorer -
# mirrors the pass/warn/block shape of every other QC gate in this codebase
# (ADR-018). A score >= PASS is accepted outright; below BLOCK triggers the
# playbook's "Automated identity retry" loop; between the two is a WARN
# surfaced for human review but not auto-retried.
IDENTITY_SIMILARITY_PASS_THRESHOLD = 7.0
IDENTITY_SIMILARITY_BLOCK_THRESHOLD = 5.0


class IdentityQCProvider(Protocol):
    """Compares a freshly generated candidate asset against a character's
    locked identity package (root reference + Character DNA) and scores how
    well the candidate preserves that identity."""

    async def score_identity(
        self, character: Character, candidate_asset: Asset, reference_asset: Asset
    ) -> QCResult: ...
