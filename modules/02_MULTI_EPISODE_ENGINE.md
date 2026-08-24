# Module 02 — Multi-Episode Engine

## Mission
Extend the current Episode-1-only implementation into a serialized episode engine that can generate, validate, commit and resume Episode 1..N.

## Build
Use Season Plan + current canonical snapshot + relevant recent recap/context to generate each episode. Separate outline, script, scenes, shots, QC and canon commit. Canon for Episode N+1 must reflect only approved prior episodes. Persist generation status per episode and support regeneration without corrupting later canon.

Implement bounded context building from structured canon rather than dumping all previous scripts. Add episode recap generation as convenience context, never as source of truth.

## Workflow
`season plan -> episode N outline -> script -> scenes/shots -> story QC -> approval -> canon commit -> episode N+1`.

Support generating one episode, a range, or the next unfinished episode. Make reruns idempotent/versioned.

## Tests
Test 3+ episode serialization, knowledge/reveal propagation, failed episode not entering canon, resume after failure, and regeneration/version behavior.

## Acceptance
Trial 01 can generate all three episodes with correct evolving canon and reopen/resume from database.

## Agent instructions
Audit existing `episode_stage`, `orchestrator`, `canon_commit`, DB and APIs before modifying. Preserve current XER-001 behavior where compatible. Add migrations/tests/docs/changelog, run full suite, commit, proceed to Module 03.