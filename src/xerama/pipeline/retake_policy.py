"""Deterministic QC-failure -> repair-action classification (MODULE-045).

Same "keyword/dimension heuristic, not an LLM call" precedent as
`pipeline/canon_commit.py:classify_change_type` and
`pipeline/sfx_derivation.py` - the mapping only needs to know *which*
MODULE-044 QC dimension BLOCKed, not interpret free-text meaning, so a
cheap, instant, fully auditable heuristic is the right tool.

Priority order (first match wins) reflects "the smallest sensible scope":
an identity/style miss is usually fixable by giving the provider better
references before spending a generation call on anything fancier; a
framing/continuity/motion miss is usually a prompt problem; a technical
media_health failure suggests the provider itself misbehaved, so try
another one; anything else just gets a fresh, unmodified attempt.
"""

from xerama.domain.enums import MediaQCDimension, QCStatus, RepairAction
from xerama.domain.media_qc import MediaQCAttempt

_STRONGER_REFERENCE_DIMENSIONS = frozenset({MediaQCDimension.IDENTITY, MediaQCDimension.STYLE})
_PROMPT_REPAIR_DIMENSIONS = frozenset(
    {MediaQCDimension.COMPOSITION, MediaQCDimension.CONTINUITY, MediaQCDimension.MOTION}
)
_ALTERNATE_PROVIDER_DIMENSIONS = frozenset({MediaQCDimension.MEDIA_HEALTH})


def classify_repair_action(attempts: list[MediaQCAttempt]) -> RepairAction:
    blocked_dimensions = {a.dimension for a in attempts if a.status == QCStatus.BLOCK}
    if blocked_dimensions & _STRONGER_REFERENCE_DIMENSIONS:
        return RepairAction.STRONGER_REFERENCES
    if blocked_dimensions & _PROMPT_REPAIR_DIMENSIONS:
        return RepairAction.PROMPT_REPAIR
    if blocked_dimensions & _ALTERNATE_PROVIDER_DIMENSIONS:
        return RepairAction.ALTERNATE_PROVIDER
    return RepairAction.FULL_RETAKE
