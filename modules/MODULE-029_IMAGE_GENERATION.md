# MODULE-029 — Image Generation

**Status:** BUILD
**Depends on:** 024,027,028,031,040

## Objective
Generate final keyframes/reference stills through replaceable image providers.

## Requirements
- Define ImageProvider capability contract and fake provider.
- Support reference images, aspect ratio, seed/parameters where available.
- Persist every take immediately with provider/model/prompt lineage.
- Run image QC before marking accepted.

## Verification
Fake provider, routing, persistence, retry and rejection tests; live provider optional.

## Done when
An approved storyboard can yield an accepted persistent 9:16 keyframe without vendor coupling; commit/push.