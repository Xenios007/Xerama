# MODULE-071 — Testing Architecture

**Status:** AUDIT/EXTEND
**Depends on:** all implemented core modules

## Objective
Standardize fast deterministic tests across domain, persistence, providers, workers, media and frontend.

## Requirements
- Define unit/integration/E2E boundaries and fixtures.
- Fake providers must make external calls unnecessary for CI.
- Temporary DB/storage isolation.
- Coverage expectations for critical state transitions and failure paths.

## Verification
Run complete backend/frontend test commands from a clean checkout.

## Done when
Contributors/agents can verify changes reproducibly without paid APIs; commit/push.