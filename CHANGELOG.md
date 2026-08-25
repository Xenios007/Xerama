# Changelog

All notable changes to Xerama are recorded here.

## [Unreleased]

### Added (MODULE-078 - Migration Strategy)

- Portability audit (clean): no SQLite-dialect imports/raw SQL beyond
  the portable readiness-check query; every migration uses generic
  `sa.*` DDL.
- `tests/test_repository_contracts.py` - reflects over every repository
  Protocol and asserts its `SQLAlchemy*` implementation exists,
  implements every method, with matching parameter names - catches a
  class of bug (typo'd/renamed argument) Python's structural typing
  never checks at import time. Ran clean against all 26 pairs.
- `docs/DEPLOYMENT.md` section 7.1 - concrete data export/import and
  asset-key-mapping guidance: app-generated UUIDs need no ID remapping;
  `storage_path` already IS the object key an S3/GCS adapter would use,
  so no key-mapping table is needed for asset migration.
- 53 new tests; full suite green (742 passed + 2 skipped, up from 689 +
  2).

### Added (MODULE-077 - Backup/Recovery)

- `python -m xerama.backup backup|verify|restore` - a consistent SQLite
  snapshot (via the sqlite3 backup API, not a raw file copy) plus a
  full asset-store copy, with a SHA-256 manifest; `restore` refuses to
  touch anything if any file fails verification.
- Version lineage and Alembic migration state preserved automatically
  (both live inside the one SQLite file backed up).
- Hosted strategy documented (`docs/DEPLOYMENT.md`) - pg_dump/object-
  storage-native backups instead of this script for a hosted deployment.
- 10 new tests including the module's own "backup -> delete -> restore
  -> verify" bar run literally as one test; also verified by hand via
  the real CLI. Full suite green (689 passed + 2 skipped, up from 679 +
  2).

### Added (MODULE-076 - Failure Simulation)

- `tests/test_failure_simulation.py` - one place the whole failure
  matrix (timeout, rate limit, quota, corrupt media, worker crash/
  restart, unavailable provider, failed QC) is inspectable together;
  most classes already had scattered coverage, this consolidates and
  adds a few new angles: quota fails on the first attempt (never
  retried - not in `RETRIABLE_KINDS`), a worker crash on one job leaves
  a second untouched job independently claimable, and a QC provider
  that always blocks drives the full auto-heal budget to `escalated`
  with zero accepted assets among the rejected retries.
- Found and corrected a documentation mismatch while writing this: the
  "storyboard is marked `escalated`" language in MODULE-045's own
  docstring means the boolean `Storyboard.escalated` field, not
  `status == "escalated"` (`status` stays `"draft"`).
- 10 new tests; full suite green (679 passed + 2 skipped, up from 669 +
  2). Completes the MODULE-071-076 testing-architecture cluster.

### Added (MODULE-075 - End-to-End Production Testing)

- `tests/test_e2e_production.py` (`@pytest.mark.e2e`) - `pytest -m e2e`:
  one continuous, deterministic, no-paid-API run through the whole
  architecture (concept -> canon -> scripts -> shots -> image/video/
  audio generation+QC+accept -> subtitles -> render -> approve -> export
  -> approve), then a full app/engine teardown and rebuild against the
  same DB/storage (a real restart, not just a fresh session) re-verifies
  everything, including that the final rendered asset's bytes are still
  readable from disk.
- Frontend smoke flow documented in `docs/TESTING.md` as a manual
  developer checklist (no browser-automation harness in this codebase).
- 1 new test; full suite green (669 passed + 2 skipped, up from 668 + 2).

### Added (MODULE-074 - Integration Testing)

- `tests/test_integration.py` (`@pytest.mark.integration`, registered
  marker) - `pytest -m integration` / `-m "not integration"` give a
  dedicated command for cross-subsystem tests.
- Story pipeline and media-generation/QC lifecycle re-verified with a
  fresh session reading back what an earlier session/commit wrote.
- New: a full worker-crash-and-resume integration test ("worker A"
  claims and crashes, "worker B" - a separate session/instance -
  reclaims the abandoned lease and completes the job) - closes a real
  gap plain repository-level lease tests didn't fully close.
- New: real FFmpeg/ffprobe tests, `skipif` when the binaries aren't
  installed (verified to skip cleanly here), synthesizing the test clip
  via ffmpeg's own `lavfi` generator.
- 5 new tests (3 always-run, 2 conditionally-skipped); full suite green
  (668 passed + 2 skipped, up from 665 passed).

### Added (MODULE-073 - Media Evaluation Framework)

- `domain/enums.py::ShotClass` (identity/dialogue/motion/establishing/
  multi-character) + `eval/media_datasets.py` - curated image (4) and
  video (2) benchmark cases, every shot class covered, mapped to the
  `MediaQCDimension`s that matter for it.
- `pipeline/media_eval_harness.py` - runs a case through the real
  `MediaProviderRouter`, persists the result via the real `AssetService`,
  scores it via the real `MediaQCProvider` contract (MODULE-044); a QC
  failure is caught and recorded rather than crashing the run.
- `pipeline/media_eval_aggregation.py` - groups by `(shot_class,
  provider)`, ADR-024's cost-per-accepted ratio over each provider's
  self-reported `estimated_cost_usd` (never conflated with real billing
  telemetry).
- New `media_eval_run_results` table + `POST /media-eval/{asset_type}/run`,
  `GET /media-eval/benchmark`, `POST /media-eval/runs/{id}/human-preference` -
  "live eval opt-in," not project-scoped.
- 21 new tests, no real provider call anywhere in the eval test suite;
  full suite green (665 passed, up from 644).

### Added (MODULE-072 - AI Evaluation Framework)

- `eval/datasets.py` - versioned dataset (`v1`) covering the LLM roles
  that actually make a call today (concept generator, judge, episode
  writer); `CONTINUITY_CHECKER` documented as N/A (deterministic check,
  no LLM role exists to benchmark).
- `pipeline/eval_quality.py` - deterministic 0-10 rubric scoring per
  schema, `(score, reasons)` always.
- `pipeline/eval_harness.py` / `pipeline/eval_aggregation.py` - runs a
  case through the real `AIGateway`, aggregates strictly by `(role,
  provider, model)` - never averages across roles.
- New `eval_run_results` table (append-only) + `POST /eval/roles/{role}/run`,
  `GET /eval/roles/{role}/benchmark`, `POST /eval/runs/{id}/human-preference` -
  "live eval opt-in," never automatic.
- 26 new tests, all against `FakeLLMProvider` (no real network call in
  any eval test); full suite green (644 passed, up from 618).

### Added (MODULE-071 - Testing Architecture)

- `docs/TESTING.md` - unit/integration/E2E boundaries, fake-provider
  inventory, isolation conventions, coverage baseline.
- `pytest-cov` added; `pytest --cov=xerama` gives 87% overall, ~100%
  across domain/most-of-pipeline/repository-interfaces.
- Found and fixed two real gaps the coverage run surfaced: `cli.py` had
  0% coverage (a second, independently-wired pipeline entrypoint never
  exercised under test - now covered end-to-end with a faked LLM
  provider); `providers/identity_qc.py` was confirmed-dead code (0%
  coverage, superseded by MODULE-044, nothing imported it) - deleted.
- 3 new tests; full suite green (618 passed, up from 615). Frontend
  suite (27 tests/7 files) and typecheck/lint/build all verified clean.

### Added (MODULE-070 - Production Hardening)

- FFmpeg/ffprobe subprocess calls now have a timeout
  (`providers/subprocess_utils.py`, `Settings.ffmpeg_timeout_seconds`,
  default 300s) - previously a malformed input could hang the process
  (and the synchronous request handling it) indefinitely.
- Unhandled exceptions are now always logged with structured,
  correlation-ID-tagged context (`api/middleware.py`) - the client
  response was already a safe generic 500, but nothing was recording
  what actually broke.
- `pool_pre_ping=True` on the DB engine (hardening aimed at a future
  hosted PostgreSQL deployment).
- Explicit audit confirmed no debug-only shortcuts exist
  (`debug=True`/`allow_origins=["*"]`/`reload=True`/TODO-FIXME-HACK) and
  partial-provider-outage handling is already solid
  (`test_media_router.py`).
- New large-project smoke tests (40-episode series generation, 300-asset
  listing) complete well within budget.
- Documented (not fixed - out of scope) two pre-existing gaps: worker-
  lease recovery has no periodic caller yet (no out-of-process worker
  exists to need it), and the MODULE-068-discovered `get_or_create`
  TOCTOU race.
- 8 new tests; full suite green (615 passed, up from 607).

### Added (MODULE-069 - Deployment Architecture)

- `docs/DEPLOYMENT.md` - component topology, local/container quickstart,
  environment separation, startup sequence, and the documented (not yet
  implemented) PostgreSQL/object-storage hosted path.
- `Dockerfile` (python:3.12-slim + ffmpeg, migrate-then-serve) and
  `docker-compose.yml` (persistent volume, health check).
- `.env.example` brought back in sync with `config.py` (MODULE-066/067/068
  settings were missing).
- `scripts/smoke_test.sh` - fresh venv, real install, migration, uvicorn
  boot, health/readiness polling. Actually run against this repo; caught
  and fixed a Git Bash/MSYS path-translation bug in the process
  (untranslated POSIX path silently breaking SQLite's DSN on Windows).

### Added (MODULE-068 - Rate Limits/Abuse Protection)

- `pipeline/rate_limiting.py` - in-memory `RateLimiter` (process
  lifetime, `app.state.rate_limiter`): sliding-window request-rate
  check, per-project concurrency slots, duplicate-in-flight-request
  suppression.
- `services/budget_service.py` - `BudgetGuard` hard ceiling check
  against real cost records (never fabricates unknown cost).
- `api/rate_limiting.py` - `guarded_generation` wraps the provider call
  in every expensive endpoint (keyframe/video/dialogue generation +
  auto-heal/lip-sync, generate-series, episode generate/next/range);
  429+Retry-After / 402 / 409 on the respective guard tripping.
- All new `Settings` fields default to permissive/unlimited - standard
  mode and the full pre-existing 587-test suite are unaffected; hosted
  deployments tighten via env vars.
- Found (documented, not fixed here - out of scope) a pre-existing
  TOCTOU race in `StyleBibleRepository.get_or_create`-style methods
  under true concurrent first callers.
- 20 new tests; full suite green (607 passed, up from 587).

### Added (MODULE-067 - Authentication/Authorization)

- `User`/`AuthSession`/`ProjectMembership` (owner/editor/viewer) +
  `POST/GET /auth/register|login|logout|me`; `hashlib.scrypt` password
  hashing, opaque bearer session tokens (no JWT/custom crypto).
- `api/authorization.py` - `authorize_project_access` + per-ID-shape
  `Depends()` factories (`require_project_role`/`require_series_role`/
  `require_episode_role`/`require_character_role`), all a true no-op
  unless `xerama_mode=hosted`.
- Every project-scoped router now enforces role-based access in hosted
  mode: projects, assets, costs, episodes, feedback, generation,
  health/observability, inspect, jobs, optimization, analytics,
  storyboards, video/audio-production, assembly, style-bible, season,
  characters, voice-profile, subtitles, music/sfx cues. `POST /projects`
  grants the creator OWNER; `GET /projects` is scoped to the caller.
- Fixed a naive/aware datetime comparison bug in
  `SQLAlchemyAuthSessionRepository` (SQLite drops tzinfo on round-trip)
  and a standard-mode behavior leak in the new `require_*_role` helpers
  (existence checks ran before the hosted-mode gate) - both caught by
  the new test suite before reaching the API layer.
- 23 new tests; full suite green (587 passed, up from 564), the entire
  564-test standard-mode suite unaffected.

### Added (MODULE-066 - Security)

- Threat-model pass over API/uploads/asset-serving/FFmpeg subprocesses/
  secrets/logs; path traversal, subprocess construction, and secret
  handling were already sound (verified with new regression tests, not
  changed).
- Fixed the one real gap: `POST /assets/upload` now validates
  content-type against a per-`AssetType` allow-list plus a fixed
  dangerous-content-type denylist (closes a stored-XSS vector via
  `GET /assets/{id}/download` echoing an attacker-declared
  `Content-Type`), enforces `Settings.max_upload_size_bytes` (413), and
  sanitizes the filename extension before it reaches the
  content-addressed storage path (415/200 as appropriate).
- `pip-audit` added as a dev dependency for manual dependency
  vulnerability scanning (no CI yet - MODULE-069/070).
- 23 new tests; full suite green (564 passed, up from 541).

### Added (MODULE-061-065 - Analytics Ingestion, Retention Analytics, Story
Performance Learning, Provider/Model Optimization, Human Feedback)

- `EpisodeMetric`/`HumanFeedback` domain models + tables
  (`episode_metrics`, `human_feedback`, revision `e5f6a7b8c9d0`).
- MODULE-061: manual-payload metrics ingestion, idempotent upsert keyed
  on (episode, render_version, source, window).
- MODULE-062: `summarize_retention` (averages only present values) +
  `map_drop_points_to_shots` (platform drop-off timestamps mapped onto
  the specific scene/shot on screen via the shared cumulative-offset
  shot-timeline walk).
- MODULE-063: `analyze_cliffhanger_performance` - cliffhanger-type vs.
  retention correlation, suppressed below a documented minimum sample
  size (3), read-only/advisory, never auto-rewrites story decisions.
- MODULE-064: `rank_providers` - composite provider/model ranking from
  real cost/QC/acceptance data across 4 objectives
  (quality/budget/speed/balanced) per ADR-024; `MediaQCRepository.list_by_assets`
  added (bulk, no N+1).
- MODULE-065: human feedback (decision/reason/rating/tags) with
  provider/model denormalized from asset provenance at write time.
- New endpoints: metrics import/list, retention summary/drop-points,
  story-performance, provider-rankings, asset/project feedback.
- 31 new tests (11 + 6 + 4 + 6 pipeline/service/repository + 4 API);
  full suite green (541 passed, up from 510).

### Added (MODULE-060 - Review/Approval Studio) - frontend (MODULE-055-060) complete

- `AssetRepository.list_by_ownership`/`GET /assets` gain a `status`
  filter (the one backend gap - "queue awaiting-review items"
  project-wide).
- `ReviewApprovalStudioPage` - pending-assets queue (expandable QC
  evidence/repair recommendation, approve/reject-with-required-reason)
  + episode publish approval (explicit per-version approve, MODULE-047).
- 4 new Vitest tests (27 total) + 1 backend test; typecheck/lint/build
  clean; Python suite 510.
- **MODULE-055-060 (Frontend) complete**: shell + Dashboard/Story/
  Character/Production/Review, all real and API-backed.

### Added (MODULE-059 - Production Studio)

- No backend changes needed - existing storyboard/video/audio/job
  endpoints covered everything.
- `ProductionStudioPage` - shot grid joining the shot plan against
  storyboard/video/audio production status by (scene, shot); per-medium
  generate buttons chain create/generate/accept in one click; video
  generation gated on storyboard approval; All/Waiting/Complete filters;
  a recent-jobs panel.
- 5 new Vitest tests (23 total); typecheck/lint/build clean; Python
  suite unaffected (510).

### Added (MODULE-058 - Character Studio)

- No backend changes needed - Module 05/MODULE-034/Module 04 already
  covered every read/write this page needs.
- `CharacterStudioPage` (cast roster) + `CharacterDetailPage` (DNA,
  provenance - unlicensed/missing-consent visually flagged, reference
  gallery, voice, wardrobe/physical-state variants, visual-takes accept/
  reject, two-step recast confirmation with a stale-dependent-asset
  warning).
- 4 new Vitest tests (18 total); typecheck/lint/build clean; Python
  suite unaffected (510).

### Added (MODULE-057 - Story Studio)

- New backend read endpoints: `GET /projects/{id}/concept-candidates`
  / `/judge-decisions` (new `ConceptRepository.list_candidates`/
  `list_judge_decisions`), `GET /episodes/{id}/quality-reports` (new
  `EpisodeRepository.list_quality_reports`), `GET
  /series/{id}/canon-events`.
- `StoryStudioPage` - Series Bible, concept lineage, season plan (with
  approve), episodes (generate-next with QC badges), canon state.
- 3 new backend tests + 1 API test; 3 new Vitest tests (14 total);
  typecheck/lint/build clean.

### Added (MODULE-056 - Project Dashboard)

- `DashboardPage` - project cards (status badge, description, created
  date, archive action), archived projects collapsed separately, create
  flow clears/disables correctly.
- `useArchiveProject`/`useGenerateSeries` query hooks.
- `ProjectDetailPage` gains a "start a series" (`CreativeBrief`) form for
  a project with no series yet, surfacing pipeline errors via the shared
  `ApiError` pattern.
- 4 new Vitest tests (11 total); typecheck/lint/build clean; Python
  suite unaffected.

### Added (MODULE-055 - Frontend Architecture)

- New `frontend/` npm project - React 19 + TypeScript + Vite + React
  Router v7 + TanStack Query v5 + Vitest/Testing Library/oxlint (chosen
  and documented in `frontend/README.md`).
- Typed API client (`api/client.ts` + `api/types.ts`) + per-resource
  TanStack Query hooks (`api/queries.ts`, polling for jobs/observability).
- `AppShell` nav layout + `router.tsx` (route tree exported separately
  for `MemoryRouter` tests) hosting `DashboardPage` (list/create
  projects), `ProjectDetailPage` (status/observability), and placeholder
  routes for Story/Character/Production/Review naming their owning
  module (057-060).
- Design system: `Button`/`Card`/`LoadingSpinner`/`ErrorBanner`/
  `QueryState`.
- Backend: `CORSMiddleware` + `Settings.cors_allowed_origins` (there was
  no CORS configuration before this module).
- 7 Vitest tests; `typecheck`/`lint`/`build` all clean; full Python suite
  (509) unaffected.

### Added (MODULE-051 / MODULE-052 / MODULE-053 / MODULE-054 - Project, Generation, Asset, Job/Progress APIs)

- `ProjectRepository.list_all`/`update`/`archive` + new
  `GET /projects`, `PATCH /projects/{id}`, `POST /projects/{id}/archive`,
  `GET /projects/{id}/status` (series/episode/current-render-version
  summary).
- `SeriesRepository.list_by_project`.
- `JobRepository.enqueue` now rejects a duplicate in-flight job for
  project/series-singleton stages (concept/judge/merge/bible/characters/
  season plan); per-episode stages are exempt (documented - no
  `episode_id` column to disambiguate safely).
- `JobRepository.list_filtered` (project/stage/status) + `GET /jobs`.
- MODULE-053 (Asset API) audited - already fully satisfied by Module 04,
  no code changes; "lock where authorized" deliberately deferred pending
  MODULE-067 (no authorization system exists yet to define "authorized").
- 14 new tests (7 project lifecycle, 4 job queue, 3 API); full suite
  (509) green.

### Added (MODULE-050 - Production Observability)

- `xerama/observability/logging.py` - contextvar-backed correlation ID,
  `CorrelationIdFilter`, `JsonLogFormatter` (structured JSON logs, fixed
  field set - never prompt/payload content).
- `api/middleware.py:correlation_id_middleware` (per-request) +
  `JobWorker._process` binding (per-job) propagate the correlation ID
  automatically through everything each one calls.
- `JobRecord` gains `created_at`/`started_at`/`finished_at` (already on
  the DB row, just never surfaced) + new `JobRepository.list_by_project`.
- `ObservabilityService` - `queue_depth`/`stage_durations`/
  `provider_reliability`, all read from already-persisted MODULE-041 job
  and MODULE-049 cost data (no new tracking system).
- New API: `GET /health`, `GET /health/ready`,
  `GET /projects/{id}/observability`.
- 9 new unit tests + 3 API tests; full suite (495) green.

### Added (MODULE-049 - Production Cost Engine)

- `CostRecord` (`domain/cost.py`) - append-only per-attempt cost ledger
  (provider/model/stage/project/series/episode/scene/shot, quantity/unit,
  cost_usd + cost_known, latency, attempt, asset_id, failure_reason). No
  prompt/payload/secret fields.
- `pipeline/cost_aggregation.py` - `summarize_cost_per_accepted` (ADR-024:
  every attempt's known cost in the numerator, only accepted quantity in
  the denominator) and `cost_per_episode`.
- `AIGateway` gains an optional `cost_recorder` + optional
  project/series/episode context on `generate()` - fully backward
  compatible (default `None` = old no-persistence behavior). This
  supersedes the earlier "AI-call telemetry is disabled for this build"
  deviation note.
- `CostRecordService.record_generation_attempts` reads a `MediaProviderRouter`
  call's already-persisted `routing_attempts` and records one `CostRecord`
  per attempt - wired live at the API layer (image/video/voice `generate`
  endpoints), no new dependency added to the production services
  themselves.
- New API: `GET /projects/{id}/costs`, `GET /projects/{id}/costs/summary`.
- Migration `d4e5f6a7b8c9_add_cost_records`.
- 11 new unit/integration tests + 1 API end-to-end test; full suite (483)
  green.

### Added (MODULE-046 / MODULE-047 / MODULE-048 - FFmpeg Assembly, Episode Versioning, Vertical Export)

- `AssemblyPlan`/`RenderManifest`/`OutputSpec` (`domain/assembly.py`) +
  `pipeline/assembly_plan_builder.py:build_assembly_plan` - deterministic
  shot-plan -> render-plan construction (audio-mode-aware: only `hybrid`
  dialogue needs a separate mixed-in track; `native`/`tts_lipsync` audio
  is already embedded in the video take).
- `EpisodeAssembler` Protocol + real 4-stage `FFmpegAssembler`
  (normalize/concat/mix/subtitle-mux, explicit argv, no shell) +
  `FakeAssembler`.
- `EpisodeAssemblyService.render_episode` - exports subtitles to SRT and
  ingests them as an asset when present, resolves every input asset's
  bytes/content_hash, renders, and persists a take-numbered episode
  `Asset` with a reproducible manifest in its provenance.
- `EpisodeRender` (`domain/episode_render.py`) - versioned workflow record
  (draft/approved/superseded - "current" is a single-row invariant,
  enabling rollback via re-approving an older `superseded` row) +
  `pipeline/render_staleness.py:check_staleness` (pure, on-demand dirty
  detection against the episode's current script version/input assets).
- `ExportProfile`/`MediaProbeResult` (`domain/export.py`) +
  `MediaInspector` Protocol + real `FFprobeInspector` + `FakeMediaInspector`
  + `pipeline/export_validation.py:validate_export` (duration/aspect/
  streams/corruption + MODULE-039's subtitle readability check folded in).
  `VerticalExportService.export_episode` reuses `render_episode` rather
  than a second encode pipeline.
- New API: `POST /episodes/{id}/render`, `GET /episodes/{id}/renders[/current]`,
  `GET|POST /episode-renders/{id}[/approve|/staleness]`,
  `POST /episodes/{id}/export`.
- Migration `c3d4e5f6a7b8_add_episode_renders`.
- 28 new tests (10 plan-builder, 7 assembly-service, 8 export-validation,
  3 export-service) plus 4 new API end-to-end tests; full suite (471)
  green.

### Added (MODULE-045 - Automatic Retakes)

- `RepairAction` (stronger_references/prompt_repair/alternate_provider/
  full_retake/escalate) + `pipeline/retake_policy.py:classify_repair_action`
  - deterministic dimension-keyword mapping from a MODULE-044 QC BLOCK to
    the smallest sensible repair.
- `services/retake_service.py:AutomaticRetakeService` - pure budget/
  escalation policy (`MAX_AUTO_RETAKE_ATTEMPTS = 3`), no provider coupling.
- `Storyboard`/`ShotVideoProduction`/`ShotAudioProduction` gain
  `auto_retake_attempts`/`escalated`; new `record_retake_attempt` repo
  method; migration `b2c3d4e5f6a7_add_auto_retake_fields`.
- `StoryboardService`/`VideoProductionService`/`AudioProductionService`
  gain `generate_with_auto_heal` - generate -> QC-gate -> on BLOCK, reject
  the take with its QC reasons, then either escalate or retry with an
  adjusted request (stronger reference requirement, a QC-reasons prompt
  suffix, or an excluded-provider set) bounded by the attempt budget.
- New API: `POST /storyboards/{id}/keyframes/auto-heal`,
  `POST /video-productions/{id}/takes/auto-heal`,
  `POST /audio-productions/{id}/takes/auto-heal`.
- 15 new tests (11 policy, 1 per-service repair-then-succeed integration
  test, 1 full-budget-escalation test, 1 API end-to-end test) plus the
  full existing suite (424 tests) staying green unmodified in behavior.
- Fixed a real, reproducible-on-this-platform bug found while building
  this: `db/base.py:utcnow()` used bare `datetime.now(timezone.utc)`,
  whose resolution is coarse enough on this OS that two rows inserted
  microseconds apart (e.g. a QC attempt's own two rows, or two enqueued
  jobs) could get an identical `created_at`, silently breaking any code
  that orders by it to recover insertion order (`MediaQCRepository.
  get_latest`, `JobRepository.claim`'s FIFO tie-break -
  `test_claim_is_fifo_within_same_priority` was intermittently failing
  from this before the fix). `utcnow()` now nudges by one microsecond
  when the clock hasn't visibly advanced, keeping every timestamp real
  UTC and strictly monotonic within the process - verified with three
  consecutive full-suite runs, all green.

### Added (MODULE-044 - Multimodal QC)

- `MediaQCDimension` (identity/style/continuity/composition/motion/
  media_health/dialogue_audio) and `MediaQCAttempt` (persisted verdict:
  status, score, evidence, reasons, repair recommendation - never
  overwritten, ADR-019) - `media_qc_attempts` table + `MediaQCRepository`.
- `pipeline/media_qc_checks.py`: deterministic `check_media_health` (any
  asset type: size/dimensions/duration vs. expectation) and
  `check_dialogue_audio` (audio-specific duration plausibility) - no
  vision model, no credentials, always available. Only unambiguous
  evidence (zero-byte file, impossible negative duration) BLOCKs; a
  missing measurement WARNs (no real audio/video-duration probe is wired
  up yet).
- `providers/media_qc.py:MediaQCProvider` - generalizes the previously
  unused, Module-05-deferred `IdentityQCProvider` into one Protocol
  covering every vision-dependent dimension (identity/style/continuity/
  composition/motion). `providers/fake_media_qc.py:FakeMediaQCProvider`
  (scripted-queue pattern, defaults to PASS) is what's actually wired up
  today - no real (paid/free) vision-capable QC model exists yet.
- `services/media_qc_service.py:MediaQCService` - runs a dimension check
  (deterministic or provider-backed), persists the attempt, and
  `run_gate` raises `QCGateBlockedError` if any dimension comes back
  BLOCK.
- **Acceptance is now gated**: `StoryboardService.accept_keyframe`
  (MEDIA_HEALTH + COMPOSITION, +STYLE/+IDENTITY when style DNA/character
  references are supplied), `VideoProductionService.accept_take`
  (MEDIA_HEALTH + MOTION, +CONTINUITY against the continuity-group
  predecessor's extracted frame, +IDENTITY when character references are
  supplied), and `AudioProductionService.accept_take` (MEDIA_HEALTH +
  DIALOGUE_AUDIO) all run their gate before flipping the asset to
  ACCEPTED. `QCGateBlockedError` -> HTTP 409 on the three accept
  endpoints. New `GET /assets/{id}/qc` lists every attempt.
- 24 new tests (deterministic checks incl. every PASS/WARN/BLOCK path,
  fake provider, repository, service `run_check`/`run_gate`, and one
  BLOCK-path integration test per production service plus one at the API
  layer) plus the full existing suite (400 tests) staying green
  unmodified in behavior - the fake provider defaults to PASS, so every
  existing accept_* call site keeps working exactly as before.

### Added (MODULE-041 / MODULE-042 / MODULE-043 - Job Queue, Worker Architecture, Retry/Recovery)

- `GenerationJob` gains queue fields (`priority`, `payload`,
  `depends_on_job_id`, `scheduled_at`, `max_attempts`, `lease_owner`,
  `lease_expires_at`) - additive alongside the existing synchronous
  `JobRunner` path, which is untouched.
- `JobRepository`: `enqueue`/`claim` (atomic, race-safe -
  `UPDATE ... WHERE status='queued'`)/`heartbeat`/`succeed_job`/
  `fail_job_attempt` (retriable -> requeue with exponential backoff;
  otherwise -> dead-letter)/`cancel`/`recover_abandoned`/`list_queued`/
  `list_failed`.
- `worker/job_worker.py:JobWorker`: stage-handler registry,
  `run_once`/`run_forever` with graceful shutdown and concurrency lanes.
  Retry classification reuses `ProviderError`/`ProviderErrorKind` (no
  second error-classification system).
- New API: `POST /jobs/enqueue`, `GET /jobs/queued`, `GET /jobs/failed`,
  `POST /jobs/{id}/cancel`.
- Migration with explicit `server_default` values, verified
  forward-compatible against a non-empty `generation_jobs` table.
- 30 new tests (repository queue mechanics incl. a genuine two-session
  claim-race test, worker dispatch/retry/dead-letter/lifecycle, API).
- Fixed a real SQLAlchemy dirty-attribute-tracking bug found while
  building this: an in-memory attribute that round-trips back to its
  originally-loaded value before a flush gets silently dropped from the
  UPDATE - fixed via `AsyncSession.refresh()` after `claim()`'s raw
  Core-level update.

### Added (MODULE-021 gap closure - Director Engine)

- `Shot.production_priority` (`ProductionPriority`: low/normal/high,
  default normal) - the one field missing from the earlier MODULE-021
  audit. Purely informational until a worker/scheduler exists to act on
  it (MODULE-041/042). MODULE-021 is now fully closed.

### Added (MODULE-039 - Subtitle Engine)

- `SubtitleCue`: text/wrapped-lines/timing/optional character attribution
  per dialogue shot.
- `pipeline/subtitle_generation.py`: deterministic cue derivation from the
  approved shot plan with cumulative episode-timeline offsets, greedy
  word-wrap, and SRT export/timestamp formatting.
- `SubtitleValidator.check_readability`: WARN on reading speed, line
  count, line length, or non-positive duration (9:16 safe-area/mobile
  readability guidance).
- `SubtitleService`/`SubtitleCueRepository.replace_track`: regeneration
  replaces the whole (episode, language) track rather than accumulating.
- New API: `POST /episodes/{id}/subtitles/generate`,
  `GET /episodes/{id}/subtitles[/export.srt|/validate]` (all
  `language`-scoped, default `"en"`).
- Migration for `subtitle_cues`.
- 26 new tests (domain, generation, validators, repository, service, API).

### Added (MODULE-037 / MODULE-038 - Music Engine, Sound Effects)

- `RightsMetadata`: shared license/source/rights-owner model for both cue
  types; `is_known` gates cue approval.
- `MusicCue`/`SoundEffectCue`: planning metadata + an asset pointer, no
  audio bytes of their own.
- `MusicCueService`/`SoundEffectCueService`: create (draft) -> link a
  library asset -> approve, refusing approval without a linked asset
  (`CueNotReadyError`) or with unknown/unlicensed rights
  (`PermissionError`). Re-linking a different asset resets an approved
  cue to `draft`.
- `pipeline/sfx_derivation.py`: deterministic keyword-based SFX candidate
  extraction from micro-beats/action text, capped at 2 per shot.
- New API: `POST/GET /episodes/{id}/music-cues`, `GET /music-cues/{id}`,
  `POST /music-cues/{id}/link-asset|/approve`, `DELETE /music-cues/{id}`;
  same shape for `/sound-effect-cues` plus
  `POST /episodes/{id}/scenes/{n}/shots/{n}/sound-effect-cues/derive`.
- Migration for `music_cues`/`sound_effect_cues`.
- 38 new tests (rights/domain, SFX-derivation, both repositories, both
  services, end-to-end API coverage).

### Added (MODULE-036 - Lip Sync)

- `VideoProductionService.generate_lip_synced_take`: reuses the existing
  `ShotVideoProduction` record/take-numbering (no new workflow table) -
  reads a source video + dialogue take, routes through
  `MediaProviderRouter[LipSyncProvider]`, always ingests a new take
  (sources never mutated).
- `LipSyncEligibilityError`/`_validate_lip_sync_eligibility`: rejects a
  character explicitly marked not-visible in MODULE-022's `SceneBlocking`
  before calling any provider; permissive when no structured blocking
  data exists.
- New API: `POST /video-productions/{id}/takes/lip-sync`.
- 4 new service tests + an extended end-to-end API test chaining
  video -> audio -> lip-sync generation.

### Added (MODULE-034 / MODULE-035 - Voice Generation, Dialogue/Audio Pipeline)

- `VoiceProfile`: one per character, reuses Module 05's
  `CharacterProvenance` directly for rights/consent (a licensed voice
  requires `consent_reference`, same validator as a licensed face).
  Lock/recast pattern matches `StyleBibleService`.
- `ShotAudioProduction`: per-shot workflow record with `audio_mode`
  (native/tts_lipsync/hybrid) copied from the shot plan; takes are plain
  `Asset` rows.
- `AudioProductionService.generate_dialogue_take`: routes through
  `MediaProviderRouter[VoiceProvider]` (language/max-characters
  capability filter), ingests a take-numbered audio `Asset` with full
  lineage. `upload_dialogue_take`/`accept_take`/`reject_take`/
  `list_takes` mirror the rest of the codebase's production services.
- New API: `GET/PATCH /characters/{id}/voice-profile[/lock|/unlock]`,
  `POST /episodes/{id}/scenes/{n}/shots/{n}/audio-production`,
  `GET /episodes/{id}/audio-productions`, `GET /audio-productions/{id}`,
  `POST /audio-productions/{id}/takes/generate|upload`,
  `GET /audio-productions/{id}/takes`,
  `POST /audio-productions/{id}/takes/{asset_id}/accept|reject`.
- Migration for `voice_profiles`/`shot_audio_productions`.
- 21 new tests (voice profile domain/repository/service, audio
  production repository/service/API coverage).

### Audited (MODULE-040 - Media Asset Storage)

- Already fully satisfied by Module 04's `StorageProvider`/`AssetService`
  - no changes needed.

### Added (MODULE-033 - Character Motion / Performance)

- `MicroBeat` gained `character_id`/`pose`/`expression`/`gaze`/
  `camera_note` (all optional, no migration needed - already JSON).
- `DirectorValidator.check_motion_plan`: BLOCK on inverted/out-of-bounds
  beat timing or same-character overlapping beats (impossible
  simultaneous pose/expression), WARN on overloaded beat density
  (>1 beat/second). Wired into `EpisodeEngine`'s Director-QC pass.
- 9 new tests (domain, all validator outcomes).

### Added (MODULE-030 - Image Editing / Regeneration)

- `ImageEditRequest` + `ImageProvider.edit` (provider-supported edit/mask
  path), routed only to providers whose `capabilities.supports_edit`
  (and `supports_mask` when a mask is given) is `True`.
  `FakeImageProvider.edit` added.
- `StoryboardService.edit_keyframe`: always produces a new take
  referencing the base asset (and mask, if any) in its lineage - the
  base take's row is never modified. "Strengthen references / change
  provider" needs no new mechanism - already composes from
  `ConsistencyPolicy` and the router's existing fallback.
- New API: `POST /storyboards/{id}/keyframes/edit`.
- 10 new tests (fake-provider edit behavior, service lineage/base-
  untouched/capability-rejection, API edit flow + rejection).

### Audited (MODULE-029 - Image Generation)

- Already fully satisfied by Module 06/07's `ImageProvider` +
  `StoryboardService.generate_keyframe` - no changes needed. QC-before-
  accept is correctly deferred to MODULE-044 (not a MODULE-029 dependency).

### Added (MODULE-022 - Scene Blocking)

- `CharacterBlock`/`MovementBeat`/`SceneBlocking` domain contracts
  (lightweight left/center/right + depth positions, visible/speaking/
  reacting flags, `occluded_by`, `screen_direction`) - `Shot.blocking_plan`
  is optional and additive alongside the existing free-text `blocking`.
- `DirectorValidator.check_scene_blocking`: BLOCK on missing
  `CharacterBlock` entries for a shot's characters, WARN on undocumented
  position/depth overlap between visible characters, WARN on
  `screen_direction` disagreement within a `continuity_group`. Wired into
  `EpisodeEngine`'s existing Director-QC pass.
- Migration for `shots.blocking_plan`.
- 9 new tests (domain defaults/JSON round-trip, all three validator
  outcomes, repository round-trip).

### Audited (MODULE-003 through MODULE-021/023)

- Domain contracts, persistence, repositories, AI gateway, model
  registry/health, creative brief through story-quality/director/shot-
  planning engines all already substantially implemented from earlier
  work this session - confirmed against each module's requirements, no
  rebuild needed. MODULE-022 was the first genuine gap found.

### Fixed (MODULE-001/002 audit - Core Platform Architecture, Configuration & Environment)

- `domain/asset.py` no longer imports `xerama.db.base` (architecture-
  boundary violation) - uses a local `_utcnow()` helper instead. Added
  `tests/test_architecture_boundaries.py` to catch regressions.
- `Settings.openrouter_api_key` is now `SecretStr` (never appears in
  `repr()`/`str()`/logs); call sites use `.get_secret_value()`.
- Added `Settings.ffmpeg_path` (env `FFMPEG_PATH`) instead of a hardcoded
  `"ffmpeg"` binary name in `FFmpegFrameExtractor`.
- New `tests/test_config.py` (defaults, env override, secret redaction,
  model-role registry fallback/override).

### Added (MODULE-032 - Video Generation, formerly Module 08 - Video Production)

- `ShotVideoProduction`: per-shot video workflow record (draft/approved +
  approved-take pointer + extracted-last-frame pointer), mirroring
  Module 06's `Storyboard` pattern; video takes stay plain `Asset` rows.
- `VideoProductionService`: `generate_take` routes through
  `MediaProviderRouter[VideoProvider]` (capability filter via
  `matches_requirements`, health/fallback reused from Module 07),
  `upload_take` manual fallback, `accept_take`/`reject_take` via
  `AssetService` (never overwrites a take).
- Continuity sequencing: shots sharing a `continuity_group` must generate
  in order - `ContinuityOrderingError` if a shot's immediate predecessor
  hasn't been accepted+last-frame-extracted yet. `accept_take` extracts
  the take's actual last frame and threads it into the next shot's
  `first_frame` input (better continuity anchor than the storyboard
  keyframe). No cascading invalidation of other shots on failure/rejection.
- `FrameExtractor` contract: `FFmpegFrameExtractor` (real, shells out to
  ffmpeg, untested here) + `FakeFrameExtractor` (what tests run against).
  App auto-selects the real one only if `ffmpeg` is on `PATH`.
- `AssetService.ingest_bytes`/`ingest_file`/`ingest_from_url` gained
  `width`/`height`/`duration_seconds` (Module 04 gap-fill, needed to
  record a video take's duration).
- New API: `POST /episodes/{id}/scenes/{n}/shots/{n}/video-production`,
  `GET /episodes/{id}/video-productions`, `GET /video-productions/{id}`,
  `POST /video-productions/{id}/takes/generate|upload`,
  `GET /video-productions/{id}/takes`,
  `POST /video-productions/{id}/takes/{asset_id}/accept|reject`.
  Shared shot/episode-lookup logic extracted to `api/shot_lookup.py`
  (de-duplicated out of `storyboards.py`).
- Migration for `shot_video_productions`.
- 22 new tests (frame extractor, video-production repository incl.
  continuity-predecessor lookup, service take-numbering/capability-
  rejection/continuity-ordering/continuity-chaining/resume/reject-retry/
  manual-upload, end-to-end API coverage).

### Added (Module 07 - Media Provider Registry & Router)

- `VideoProvider`/`VoiceProvider`/`LipSyncProvider` capability contracts +
  `FakeVideoProvider`/`FakeVoiceProvider`/`FakeLipSyncProvider` (scripted
  bytes-or-`ProviderError` queue, same pattern as `FakeLLMProvider`/
  `FakeImageProvider`). `providers/video.py:matches_requirements` filters a
  video provider's capabilities against a shot's `ProviderRequirements`
  (Module 03).
- `MediaProviderRouter` (`services/media_router.py`): one generic router
  over any provider type - capability filter -> health filter (reuses
  `ProviderHealthTracker`/`ProviderError`, no second health/error system)
  -> priority order (deterministic, stable tie-break) -> attempt -> record
  reason -> fall back to the next eligible provider. Raises
  `NoEligibleProviderError` with every attempt's outcome when nothing
  works.
- `StoryboardService.generate_keyframe` now takes a
  `MediaProviderRouter[ImageProvider]` instead of a single provider, so
  image keyframe requests route/fall back across every registered image
  provider instead of a hardcoded one; routing attempts are recorded in
  the resulting asset's provenance.
- `app.state.image_router`/`video_router`/`voice_router`/`lip_sync_router`
  wired in the app lifespan, each seeded with one fake provider (no real
  credentialed adapter available); video/voice/lip-sync routers are ready
  for Modules 08/09 to consume.
- 20 new tests (deterministic priority ordering + stable tie-break,
  capability filtering, health-circuit skip, fallback-after-failure,
  exhausted-fallback error, fake video/voice/lip-sync provider round
  trips, `matches_requirements` coverage).

### Added (Module 06 - Style Bible, Storyboard & Image Production)

- `StyleBible` (ADR-013): one production-anchor row per series
  (style asset/DNA/palette/lighting/texture/color-temperature/composition
  rules/negatives), locked/versioned the same way as `Character`
  (Module 05) - `StyleBibleService.update` blocked while locked,
  `unlock_for_recast` bumps `version`.
- `Storyboard`: one per-shot workflow record (draft/approved +
  approved-keyframe pointer). Keyframe takes are plain `Asset` rows
  (Module 04, `type=image`, `take_number`) - no new asset-like entity.
- `ImageProvider` contract + `ImageProviderCapabilities` + `FakeImageProvider`.
  `StoryboardService.generate_keyframe` rejects an incompatible provider
  (unsupported aspect ratio / unsupported references) before calling
  `generate()`, resolves compiled reference ids to bytes via `AssetService`,
  and ingests the result as a take-numbered `Asset`; `upload_keyframe` is
  the manual-upload fallback. Reject leaves the storyboard in `draft` for
  a retry with an incremented take number.
- `PromptCompiler.compile_shot`/`compile_episode` now take an optional
  `StyleBible` and populate `style_dna`/`references.style_asset_id`/
  negative constraints from it - closes the Module 03 gap where
  `style_dna` was always `""`.
- `AssetRepository.list_by_ownership` gained `scene_number`/`shot_number`
  filters (alongside Module 05's `character_id`).
- New API: `GET/PATCH /series/{id}/style-bible[/lock|/unlock]`,
  `POST /episodes/{id}/scenes/{n}/shots/{n}/storyboard`,
  `GET /episodes/{id}/storyboards`, `GET /storyboards/{id}`,
  `POST /storyboards/{id}/keyframes/generate|upload`,
  `GET /storyboards/{id}/keyframes`,
  `POST /storyboards/{id}/keyframes/{asset_id}/accept|reject`.
- Migration for `style_bibles`/`storyboards`.
- 32 new tests (style bible domain/repository/service, storyboard
  repository, fake image provider, storyboard service capability
  rejection/take-numbering/accept-reject-retry, Style-Bible-in-
  PromptCompiler integration, and end-to-end API keyframe workflow
  coverage).

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
