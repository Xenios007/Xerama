# MODULE-033 — Character Motion / Performance

**Status:** BUILD
**Depends on:** 023,032

## Objective
Represent acting/motion instructions explicitly so performance remains consistent and controllable.

## Requirements
- Map micro-beats to pose/action/expression/gaze/camera timing.
- Support provider capability differences for performance/subject reference.
- Detect impossible or overloaded motion plans before generation.
- Keep dialogue performance linked to speaker/emotion.

## Verification
Micro-beat timing, overloaded-shot and provider-degradation tests.

## Done when
Motion is structured production data rather than a single unbounded prose sentence; commit/push.