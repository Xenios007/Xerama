# Changelog

All notable changes to Xerama are recorded here.

## [Unreleased]

### Added (Module 01 - Season & Reveal Engine)

- `SeasonPlan` domain model (acts, mysteries, promises, reveal ladder with
  audience-knowledge tracking, escalation milestones, character-arc
  milestones, episode assignments) implementing the XER-006 macro-story
  layer between the Series Bible and per-episode generation.
- `SeasonStage` generates a validated season plan for the full requested
  episode count from the approved bible + cast.
- `SeasonValidator`: episode coverage, reveal ordering (no premature
  reveals), setup-before-payoff, resolved-thread consistency, "no
  continuation hook" warning, escalation-progression, character-arc
  coverage, and repeated-cliffhanger/no-progress checks.
- Versioned `SeasonPlanRecord` persistence (regenerations never overwrite -
  ADR-19) with a closed-loop retry (one regeneration with validator feedback
  on `BLOCK`, mirroring the existing shot-plan retry).
- `Showrunner` now generates/persists the season plan before episode
  outlines and feeds it into outline generation as binding context.
- New API: `GET/POST /series/{id}/season-plan[...]` (current, versions, one
  version, regenerate, approve).
- Alembic migration for the `season_plans` table.
- 25 new tests (domain schema, validator heuristics, repository versioning,
  updated pipeline/API coverage).

### Added

- Closed-loop QC retry: a `BLOCK`-level continuity result on the shot plan
  now triggers one targeted regeneration (script unchanged, shot plan only)
  with the QC reasons fed back into the prompt, before giving up and leaving
  the episode `BLOCK` for review (ADR-019). Every attempt's QC report is
  persisted rather than overwritten.
- Canon commit: an episode's free-text `canon_changes` are now classified
  into typed `CanonEvent`/`EpisodeStateChange` rows (keyword heuristic in
  `pipeline/canon_commit.py`) and committed only when retention and
  continuity QC did not `BLOCK` (ADR-006).
- 12 new tests covering the retry loop (success, gives-up-after-max-attempts)
  and canon-change classification/commit gating.

- Python 3.12 project skeleton (FastAPI, Pydantic v2, SQLAlchemy 2.0 async,
  Alembic, httpx, pytest) - XER-001 core architecture.
- Domain contracts for concepts, judge results, series bible, characters/
  relationships/knowledge, episode outlines/scripts, scenes/shots, canon
  events, and QC results, matching docs/JSON_CONTRACTS.md and
  docs/DATA_MODEL.md.
- SQLAlchemy persistence layer and repository interfaces/implementations for
  projects, concept candidates + judge decisions, series/bible/cast,
  episodes/scenes/shots/quality reports, and generation jobs. Initial Alembic
  migration.
- OpenRouter LLM provider with structured JSON-schema outputs and provider
  error classification; in-memory fake provider for tests/local runs.
- Model-role configuration (`ModelRoleRegistry`) resolving each logical role
  to a configurable model/temperature, defaulting to a snapshot of
  OpenRouter's free-tier catalog.
- AI gateway with JSON/schema repair-retry loop.
- Standard-mode story pipeline: dual concept candidates, AI judge (A/B/
  MERGE), series bible, cast/relationships, episode outlines, Episode 1
  script, scene/shot planning - orchestrated end to end by `Showrunner`,
  with every stage tracked as a persistent `GenerationJob` and persisted
  immediately for inspectability.
- Deterministic retention and continuity QC validators.
- HTTP API: `POST /projects`, `POST /projects/{id}/generate-series`, and
  inspect endpoints for jobs/series/bible/characters/episodes/shots.
- Local CLI entrypoint (`python -m xerama.cli`) for running the pipeline
  without a server.
- 39 tests covering schemas, repositories, the OpenRouter provider (mocked
  via respx, no network), the AI gateway's repair/retry behavior, QC
  validators, the full pipeline (including a mid-pipeline-failure case), and
  the HTTP API.

### Documented

- `docs/IMPLEMENTATION_STATUS.md` added to track implemented/partial/
  planned/blocked work and log the non-blocking documentation
  inconsistencies found while implementing (SeriesBible field set, model-
  role-to-stage assignment) and the explicit decision to disable AI-call
  telemetry for this build.
