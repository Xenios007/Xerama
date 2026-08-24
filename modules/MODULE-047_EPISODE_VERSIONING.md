# MODULE-047 — Episode Versioning

**Status:** BUILD
**Depends on:** 018,040,046

## Objective
Preserve script/shot/media/render history so edits and retakes are reversible.

## Requirements
- Version episode plans/scripts/shot sets and final renders.
- Record parent/source versions and approval state.
- Define dirty/stale propagation when upstream assets change.
- Never overwrite a published/approved version silently.

## Verification
Version lineage, rollback/reference and dirty-propagation tests.

## Done when
Every final episode can be traced to exact source assets and regenerated; commit/push.