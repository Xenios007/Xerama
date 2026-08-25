"""Identity-QC thresholds (Module 05 "QC hooks").

Module 05 deferred "multimodal implementation to Module 11"; that module is
MODULE-044 (Multimodal QC), which implements identity scoring as
`MediaQCDimension.IDENTITY` through the generalized
`providers/media_qc.py:MediaQCProvider` Protocol rather than a second,
identity-only Protocol (superseding the one originally stubbed here) -
`StoryboardService.accept_keyframe`/`VideoProductionService.accept_take`
pass character reference assets through that one interface. The thresholds
below remain the documented starting point for a real scorer's pass/block
calibration.

See research/CHARACTER_CONTINUITY_PLAYBOOK.md "Continuity scoring" and
"Automated identity retry".
"""

IDENTITY_QC_GATE = "identity_consistency"

# Placeholder thresholds pending a real multimodal scorer - mirrors the
# pass/warn/block shape of every other QC gate in this codebase (ADR-018).
# A score >= PASS is accepted outright; below BLOCK triggers the playbook's
# "Automated identity retry" loop; between the two is a WARN surfaced for
# human review but not auto-retried.
IDENTITY_SIMILARITY_PASS_THRESHOLD = 7.0
IDENTITY_SIMILARITY_BLOCK_THRESHOLD = 5.0
