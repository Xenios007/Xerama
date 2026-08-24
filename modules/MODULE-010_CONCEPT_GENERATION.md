# MODULE-010 — Concept Generation

**Status:** AUDIT/EXTEND
**Depends on:** 006,009

## Objective
Generate multiple independent microdrama concepts from one brief.

## Requirements
- Preserve Standard mode minimum two candidates.
- Keep candidate calls independent and persist all outputs.
- Include hook, protagonist goal, opposition, engine, stakes, serial potential and production feasibility.
- Support Fast/Standard/Quality candidate counts through configuration.
- Never discard rejected candidates.

## Verification
Fake-provider tests for candidate independence, persistence and failure recovery.

## Done when
Concept generation is reproducible/inspectable and does not depend on one model; commit/push.