# Changelog

All notable changes to Xerama are recorded here.

## [Unreleased]

### Added

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
