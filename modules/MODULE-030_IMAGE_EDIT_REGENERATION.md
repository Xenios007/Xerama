# MODULE-030 — Image Editing / Regeneration

**Status:** BUILD
**Depends on:** 029,044

## Objective
Repair failed stills without regenerating unrelated production assets.

## Requirements
- Support full regenerate and provider-supported edit/mask paths.
- Preserve take lineage and rejection reason.
- Strengthen references or change provider based on QC recommendation.
- Never overwrite accepted assets silently.

## Verification
Retry policy, version lineage, alternate-provider and acceptance tests.

## Done when
Image QC failures trigger targeted repair with auditable history; commit/push.