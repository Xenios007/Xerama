# MODULE-035 — Dialogue / Audio Pipeline

**Status:** BUILD
**Depends on:** 032,034

## Objective
Choose and assemble `native`, `tts_lipsync`, or `hybrid` audio per shot.

## Requirements
- Persist audio mode and dialogue source per shot.
- Preserve native ambience when hybrid mode is used.
- Align scripted dialogue with shot duration and speaker timing.
- Normalize sample format/metadata for editor.

## Verification
Mode-selection, timing, fallback and asset-lineage tests.

## Done when
Audio strategy is provider-independent and exact dialogue can be enforced when required; commit/push.