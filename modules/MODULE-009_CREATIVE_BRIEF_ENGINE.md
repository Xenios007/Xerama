# MODULE-009 — Creative Brief Engine

**Status:** AUDIT/EXTEND
**Depends on:** 003,005

## Objective
Create the authoritative input contract for a drama production.

## Requirements
- Persist title/premise, genre, audience, language, episode count/duration, rating/content constraints, production mode and optional budget.
- Validate sane ranges and required fields.
- Support editing/versioning before production lock.
- API/CLI must use the same contract.

## Verification
Validation, persistence and API tests.

## Done when
Every downstream story decision traces to a persisted CreativeBrief version; commit/push.