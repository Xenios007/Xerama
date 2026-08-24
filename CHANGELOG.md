# Changelog

All notable changes to Xerama are recorded here.

## [Unreleased]

### Added (Module 05 - Character Casting Studio)

- Extended `Character` with a multi-view `reference_pack`, `identity_provenance`
  (`CharacterProvenance`: `identity_type` synthetic_original/licensed_authorized
  + required `consent_reference` when licensed), `locked`, and `version` -
  a durable, lockable production identity package per character.
- New `WardrobeVariant`/`CharacterPhysicalStateVariant` records, each with
  their own reference asset ids - "do not prompt 'same clothes as before'."
- `CharacterCastingService`: lock/unlock-for-recast (bumps `version`),
  identity updates blocked (`PermissionError`) while locked, wardrobe/
  physical-state variants addable regardless of lock state.
- `ConsistencyPolicy` (ADR-014): centralized, deterministic per-character
  reference selection (root -> reference-pack views -> wardrobe -> physical
  state, deduped, capped at a per-provider max) used for both single- and
  multi-character shots. `PromptCompiler` (Module 03) now delegates to it
  instead of inlining `visual_identity_id or character.id`; `format_character_dna`
  moved to `domain/character.py` as a shared function.
- `IdentityQCProvider` protocol + placeholder pass/block thresholds
  (`providers/identity_qc.py`) - interface only, multimodal implementation
  deferred to Module 11 per the module spec.
- `AssetOwnership.character_id` so identity/wardrobe/physical-state assets
  can be attributed to a character independent of episode/scene/shot.
- New API: `GET/POST /characters/{id}[/lock|/unlock|/identity|/provenance|
  /wardrobe|/physical-states]`.
- Migration for the new character/asset columns and the two variant tables.
- 30 new tests (identity defaults/provenance validation/DNA formatting,
  repository CRUD/lock/version/variants, service lock-immutability/recast/
  wardrobe-while-locked, consistency-policy selection/dedup/max-reference/
  multi-character isolation, and API lock-blocks-update-until-recast +
  wardrobe/physical-state endpoint coverage).

### Added (Module 04 - Asset & Storage System)

- `Asset` domain model with typed ownership (`AssetOwnership`) and full
  provenance/lineage (`AssetProvenance`) - every asset traces back to what
  produced it (ADR-020).
- `StorageProvider` protocol + `LocalStorageProvider`: path-traversal-safe
  local filesystem storage (`save_bytes`/`save_file`/`read_bytes`/`exists`/
  `delete`/`list_all`), ready for a remote/S3 implementation later without
  touching callers (ADR-022).
- `AssetService`: content-addressed ingestion (`ingest_bytes`/`ingest_file`/
  `ingest_from_url`) that hashes and dedups on-disk storage while always
  preserving one `Asset` row per ingestion event; accept/reject workflow;
  dedup-safe delete (protects `ACCEPTED` assets unless forced, never deletes
  a file another asset still references); `find_missing_files`/
  `find_unreferenced_files` reconciliation.
- New API: `GET /assets`, `GET /assets/{id}`, `GET /assets/{id}/download`,
  `POST /assets/{id}/accept`, `POST /assets/{id}/reject`,
  `DELETE /assets/{id}`, `POST /assets/upload` (multipart).
- Migration for the new `assets` table.
- `python-multipart` added as a dependency (required for FastAPI file
  uploads).
- 31 new tests (local storage path-safety and round trips, asset domain
  defaults/round-trip, asset repository CRUD/filters/status transitions,
  asset service ingestion/dedup/accept-reject/delete-protection/
  reconciliation, and end-to-end API upload/download/accept/reject/delete
  coverage).

### Added (Module 03 - Director & Prompt Compiler)

- Extended the `Shot` contract: `blocking` (free-text, not a coordinate
  system), `continuity_group`, `provider_requirements`
  (`ProviderRequirements`: T2V/I2V, first/last-frame, subject-reference,
  native-audio flags).
- `DirectorValidator`: deterministic vertical-composition,
  dialogue-coverage, and continuity-grouping checks - production-readiness
  QC, separate from and never blocking story canon commit.
- `PromptCompiler` + `ShotGenerationRequest`: pure, deterministic
  provider-neutral prompt compilation (shot intent + Character DNA + shot
  references + default negative constraints), with no vendor-specific
  syntax in the domain model. New `GET /episodes/{id}/generation-requests`
  endpoint compiles the approved shot plan on demand.
- Migration for the new `shots` columns.
- 21 new unit tests (shot-contract validation, all three director checks,
  prompt-compilation determinism/reference-selection/negative-constraints)
  plus an API test for the new endpoint.

### Added (Module 02 - Multi-Episode Engine)

- `EpisodeEngine`: generate/regenerate any episode (`generate_episode`),
  the next unfinished one (`generate_next_unfinished`), or a range
  (`generate_range`) - script -> shots (existing retry-on-BLOCK loop) ->
  story QC -> canon commit, gated the same way Episode 1 already was.
- `pipeline/canon_builder.py`: builds each episode's bounded `CanonSnapshot`
  from committed canon events + prior *committed* episode outlines only -
  never raw prior scripts.
- Regeneration safety: regenerating a committed episode retires its old
  canon events (`committed=False`, never deleted) before recommitting fresh
  ones, and marks every later committed episode `STALE`. `Episode.version`
  increments on each script regeneration.
- `Showrunner`/`EpisodeEngine` now share one `JobRunner` (extracted from the
  old duplicated `Showrunner._run_job`) instead of duplicating job
  bookkeeping.
- New API: `POST /series/{id}/episodes/{n}/generate`,
  `POST .../generate-next`, `POST .../generate-range`.
- Migration for `episodes.version`.
- 14 new tests (canon-snapshot bounding, 3-episode serialization with
  cross-episode canon propagation verified in the actual LLM prompt,
  blocked-episode-never-enters-canon, resume-retries-blocked-episode,
  regeneration marks downstream stale + replaces (not duplicates) canon,
  plus API coverage).

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
