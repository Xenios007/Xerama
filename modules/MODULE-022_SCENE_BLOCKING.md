# MODULE-022 — Scene Blocking

**Status:** BUILD
**Depends on:** 021

## Objective
Represent actor placement, eyelines, movement and camera relationship consistently across a scene.

## Requirements
- Define lightweight left/center/right/depth positions and movement beats; keep schema extensible to coordinates later.
- Track who is visible, speaking, reacting and occluding.
- Preserve screen direction across connected shots.
- Validate multi-character blocking.

## Verification
Two-person dialogue, entrance/exit and screen-direction tests.

## Done when
Shot planning can reason about spatial continuity without requiring a full 3D engine; commit/push.