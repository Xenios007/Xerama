# MODULE-032 — Video Generation

**Status:** BUILD
**Depends on:** 023,024,029,031,040,041

## Objective
Generate short shot-level clips from approved shot contracts/keyframes.

## Requirements
- VideoProvider contract: T2V/I2V, first/last frame, subject reference, native audio, duration/aspect/resolution.
- Persist every take immediately.
- Respect continuity groups: independent shots parallelizable, connected shots sequential when required.
- Extract metadata and send output to QC.

## Verification
Fake video provider, routing, job, persistence and continuity scheduling tests.

## Done when
Accepted keyframes can produce persistent shot clips without provider-specific business logic; commit/push.