# Module 08 — Video Production Engine

## Mission
Generate versioned video takes from approved keyframes and Director shot contracts.

## Build
Define provider-neutral video request/result contracts supporting T2V/I2V, first/last frame, subject references, duration, aspect/resolution, native audio and continuity groups. Implement shot-level take/version records and durable asset ingest.

Independent shots may run concurrently; continuity groups must support sequential generation and extraction of the actual final frame from Shot N for Shot N+1. Implement last-frame extraction behind a media utility (FFmpeg is acceptable).

Use fake provider for tests. Real providers remain optional/configurable.

## Failure behavior
Never overwrite accepted/rejected takes. Classify provider failures, retry according to policy, then fallback through router. Failed shots must not force regeneration of successful shots.

## Tests
Take lineage, continuity sequencing, last-frame chaining, fallback, retries, durable asset storage and resume behavior.

## Acceptance
Given approved keyframes, Xerama can produce durable shot videos with traceable takes and continuity metadata using fake providers end to end.

## Agent instructions
Update migrations/APIs/tests/docs/changelog, run suite, commit, proceed to Module 09.