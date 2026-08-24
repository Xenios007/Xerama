# MODULE-044 — Multimodal QC

**Status:** BUILD
**Depends on:** 020,029,032,040

## Objective
Apply consistent PASS/WARN/BLOCK quality gates to story, image, video and audio assets.

## Requirements
- QCProvider/vision interface plus deterministic media checks and fake scorer.
- Dimensions: identity, style, continuity, composition, motion/media health, dialogue/audio where applicable.
- Persist score, evidence, reasons and repair recommendation per attempt.
- Configurable thresholds; no single opaque score.

## Verification
Fixture-based pass/warn/block and persistence tests.

## Done when
Production assets cannot become accepted/publishable without defined QC gates; commit/push.