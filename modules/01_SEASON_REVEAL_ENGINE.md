# Module 01 — Season & Reveal Engine

## Mission
Implement the missing XER-006 macro-story layer between Series Bible and episode generation.

## Build
Create typed domain models and persistence for season arc, act/phase progression, reveal ladder, mysteries, promises/payoffs, escalation milestones, character-arc milestones, and episode assignments. Add a `season_stage` that receives approved Series Bible + cast/canon and produces a validated season plan for the requested episode count. Track audience knowledge separately from character knowledge where relevant.

The plan must prevent premature reveals, forgotten setup/payoffs, repetitive cliffhangers, and episodes that do not advance the season.

## API
Expose inspect/regenerate/approve endpoints for season architecture. Existing generation flow should persist the season plan before detailed episode generation.

## Validation
Add checks for episode coverage, reveal ordering, setup-before-payoff, unresolved end-state, escalation progression, character-arc coverage, and duplicate beats.

## Tests
Unit tests for schemas/validators/repositories plus pipeline and API tests. Existing tests must remain green.

## Acceptance
A project can generate and reopen a persisted season/reveal map covering every requested episode, and downstream episode generation can consume it without relying on full chat history.

## Agent instructions
Read `docs/ROADMAP.md`, `docs/STORY_FORMULA.md`, `docs/DATA_MODEL.md`, `docs/DECISIONS.md`, current domain/pipeline/repository code and tests first. Reuse existing patterns. Add Alembic migration(s), update docs/status/changelog, run all tests, commit logical units, then proceed to Module 02.