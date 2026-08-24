# MODULE-003 — Domain Contract System

**Status:** AUDIT/EXTEND
**Depends on:** 001

## Objective
Define stable Pydantic contracts for every production artifact and state transition.

## Requirements
- Audit existing CreativeBrief, story, canon, episode, scene, shot and QC models.
- Add IDs/version fields and enums where needed.
- Separate canonical domain objects from provider payloads.
- Preserve backward compatibility or add migrations/adapters.
- Validate durations, 9:16 production constraints, references and state transitions.

## Verification
Schema validation, serialization and compatibility tests.

## Done when
Downstream modules can rely on typed contracts without parsing arbitrary prose; full suite passes; docs updated; commit/push.