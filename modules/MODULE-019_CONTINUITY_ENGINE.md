# MODULE-019 — Continuity Engine

**Status:** EXTEND
**Depends on:** 014,018

## Objective
Detect narrative contradictions before expensive media generation.

## Requirements
- Validate chronology, relationships, knowledge, secrets, injuries/deaths, wardrobe, props, locations and established facts.
- Return PASS/WARN/BLOCK with evidence and repair suggestion.
- Support deterministic checks plus optional LLM critic.
- Never commit BLOCKed changes to canon.

## Verification
Fixture-based contradiction tests for every category and targeted repair flow.

## Done when
Known canon conflicts reliably block or warn before production; commit/push.