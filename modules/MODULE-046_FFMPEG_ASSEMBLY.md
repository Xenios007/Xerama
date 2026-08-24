# MODULE-046 — FFmpeg Assembly

**Status:** BUILD
**Depends on:** 032,035,037,038,039,040

## Objective
Deterministically assemble accepted creative assets into an episode timeline.

## Requirements
- FFmpeg/ffprobe wrapper with safe subprocess arguments and clear dependency check.
- Concatenate/trim clips, mix dialogue/music/SFX, add subtitles and normalize output.
- Produce reproducible render manifest.
- Never use generative AI for deterministic assembly.

## Verification
Small synthetic media fixtures, missing-FFmpeg behavior and manifest tests.

## Done when
Accepted assets can render into a playable episode automatically; commit/push.