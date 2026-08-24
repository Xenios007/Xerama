# MODULE-014 — Canon & Memory

**Status:** AUDIT/EXTEND
**Depends on:** 012,013

## Objective
Provide structured persistent memory for long serialized drama.

## Requirements
- Persist canon events, character state, relationships, knowledge, audience knowledge, locations, props, injuries, timeline and unresolved hooks.
- Generated changes become canon only after validation/approval.
- Replace keyword-only classification where downstream correctness requires stronger typing.
- Produce bounded context snapshots for AI calls.

## Verification
Commit/rollback, snapshot, chronology and knowledge-state tests.

## Done when
Episode N can be generated without replaying the entire series transcript and contradictions are detectable; commit/push.