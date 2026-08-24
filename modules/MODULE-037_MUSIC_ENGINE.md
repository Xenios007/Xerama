# MODULE-037 — Music Engine

**Status:** BUILD
**Depends on:** 018,040

## Objective
Plan and attach licensed/generated music cues without entangling story or editor logic.

## Requirements
- Model cue purpose, mood, start/end, ducking and source/license metadata.
- Support library asset selection first; generation provider optional.
- Prevent unlicensed/unknown provenance assets from publish-ready state.
- Expose normalized audio to editor.

## Verification
Cue planning, rights metadata and timeline tests.

## Done when
Episodes have auditable music cues ready for deterministic mixing; commit/push.