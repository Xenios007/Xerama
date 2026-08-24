# Module 11 — Multimodal QC & Retakes

## Mission
Extend current story QC into production QC with targeted repair.

## Build
Create QC interfaces/results for identity, style, continuity, composition, media health, audio/lipsync and final episode quality. Preserve `PASS/WARN/BLOCK`, score, reasons and repair recommendation. Implement deterministic media-health checks first (file readable, duration, dimensions/aspect, streams, black/empty output where practical via ffprobe/FFmpeg).

Add a multimodal-review provider interface so vision models can be swapped. Use fake reviewer tests if no suitable real vision endpoint is configured.

Implement retake policy: failed asset -> diagnose -> retry same provider with adjusted references/prompt where appropriate -> alternate provider -> human review/budget stop. Store every QC result and take; never overwrite history.

## Tests
Gate aggregation, per-character multi-character QC records, style/continuity failures, media-health blocking, retake limits, alternate provider and human-review terminal state.

## Acceptance
A failed shot is automatically isolated and repaired/re-routed without regenerating an otherwise good episode.

## Agent instructions
Reuse existing quality domain/validators and ADR-018/019. Add migrations/tests/docs/changelog, run suite, commit, proceed to Module 12.