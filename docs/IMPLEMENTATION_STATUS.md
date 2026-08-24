# Xerama Implementation Status

_Last updated: 2026-08-25 - Module 06 (Style Bible, Storyboard & Image Production)._

This tracks what actually exists in `src/xerama` against the architecture in
`docs/` and `research/`, per the project rule "when implementation reveals
an existing research assumption is wrong, update the relevant
documentation - do not silently diverge."

## Implemented

- **Project skeleton** - Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0
  (async), Alembic, httpx, pytest/pytest-asyncio. `src/xerama` package layout.
- **Domain contracts** (`xerama/domain/`) - `CreativeBrief`, `ConceptCandidate`,
  `JudgeResult`, `SeriesBible`, `Character`/`CharacterDNA`/`RelationshipState`/
  `CanonFact`, `EpisodeOutline`/`EpisodeScript`, `Scene`/`Shot`/`MicroBeat`,
  `CanonEvent`/`CanonSnapshot`, `QCResult`/`QualityScore`. All Pydantic v2,
  matching docs/JSON_CONTRACTS.md plus the reconciliation noted below.
- **Persistence** (`xerama/db/`, `xerama/repositories/`) - SQLAlchemy models
  for every entity in docs/DATA_MODEL.md (nested/flexible fields stored as
  JSON columns, relational fields as real columns - see module docstring).
  Repository Protocols in `repositories/interfaces.py` with a SQLAlchemy
  implementation in `repositories/sqlalchemy_impl.py` - pipeline code depends
  only on the Protocols (ADR-021). Alembic is wired up (`alembic/env.py` reads
  `Settings.database_url` and targets `Base.metadata`); one initial migration
  exists. `db.base.create_all` remains available as a Trial-01 dev
  convenience so `uvicorn`/the CLI can run without a manual `alembic upgrade`.
- **OpenRouter LLM provider** (`xerama/providers/openrouter.py`) - OpenAI-
  compatible `/chat/completions`, JSON-schema structured outputs, error
  classification into the taxonomy from docs/ARCHITECTURE.md section 12,
  never logs the API key. `providers/fake.py` gives a scriptable in-memory
  provider for tests/local runs with no paid call. `providers/health.py` is a
  minimal in-memory circuit breaker (ADR-011).
- **Model role configuration** (`xerama/config.py`) - `ModelRoleRegistry`
  resolves each `ModelRole` to an env-overridable model ID/temperature;
  business logic never references a model ID directly (ADR-004). Default
  free-model IDs are a snapshot of OpenRouter's `:free` catalog taken
  2026-08-24 (research/FREE_FIRST_MODEL_STRATEGY.md's "snapshot exact free
  LLM candidates" checklist item) - re-verify before relying on them.
- **AI gateway** (`xerama/pipeline/ai_gateway.py`) - single
  `generate(role, schema, ...)` entrypoint; retries + in-context JSON/schema
  repair on invalid output (docs/JSON_CONTRACTS.md Contract Rule 5); raises
  immediately on non-retriable provider errors, retries retriable ones.
- **Standard-mode story pipeline** (`xerama/pipeline/`) - dual independent
  concept candidates -> judge (A/B/MERGE, both candidates preserved) ->
  merge synthesis when needed -> Series Bible -> cast/relationships ->
  episode outlines (full requested count) -> Episode 1 script -> scene/shot
  plan. `orchestrator.py`'s `Showrunner` runs the whole thing, wrapping every
  stage in a persistent `GenerationJob` and persisting each artifact
  immediately so a mid-pipeline failure still leaves earlier stages
  inspectable (verified by `tests/test_orchestrator.py`).
- **Closed-loop QC retry** - if the shot plan's continuity QC comes back
  `BLOCK`, the Showrunner regenerates only the shot plan once more with the
  QC reasons fed back into the prompt (targeted retry, not whole-episode
  regeneration - ADR-019), before giving up and leaving it `BLOCK` for human
  review. Every attempt's QC report is persisted, never overwritten.
- **Canon commit** - an approved episode's `canon_changes` (free text) are
  now classified into typed `CanonEvent`/`EpisodeStateChange` rows via a
  keyword heuristic (`pipeline/canon_commit.py`) and committed only when
  neither retention nor continuity QC ended `BLOCK` - see ADR-006 ("output is
  not canon until validated").
- **Retention + continuity validators** (`xerama/pipeline/validators.py`) -
  deterministic heuristics per docs/STORY_FORMULA.md / ADR-018 (pass/warn/
  block + reasons + repair recommendation). Documented as initial heuristics,
  not a final scoring system.
- **API** (`xerama/api/`) - `POST /projects`, `GET /projects/{id}`,
  `POST /projects/{id}/generate-series` (runs the full pipeline synchronously
  - acceptable for Trial 01 per docs/ARCHITECTURE.md section 14), plus
  inspect endpoints for jobs/series/bible/characters/episodes/shots.
- **CLI** (`xerama/cli.py`) - `python -m xerama.cli --genre ... --premise ...`
  runs the same pipeline locally and prints the full structured result.
- **Tests** - 201 tests (see `tests/`), all against `FakeLLMProvider` /
  respx-mocked HTTP, no paid API calls required.

### Module 01 - Season & Reveal Engine (XER-006)

- **Domain** (`xerama/domain/season.py`) - `SeasonPlan` (acts, mysteries,
  promises, reveal ladder, escalation milestones, character-arc milestones,
  episode assignments). Audience knowledge is tracked separately from
  character knowledge per reveal (`RevealMilestone.audience_knowledge_before
  /_after`), matching docs/STORY_FORMULA.md section 3.
- **Season stage** (`pipeline/season_stage.py`) - generates a `SeasonPlan`
  for the full requested episode count from the approved Series Bible + cast
  (`story_architect` role, consistent with the existing role-mapping
  decision below).
- **Season validator** (`pipeline/season_validators.py`) - deterministic
  pass/warn/block checks: episode coverage, reveal ordering (a reveal can't
  precede the mystery it resolves or a reveal it depends on), setup-before-
  payoff, "resolved" threads must record a resolution/payoff episode, a
  season that resolves every thread warns (no continuation hook), escalation
  must trend upward, every character needs at least one arc milestone,
  cliffhanger types can't repeat back-to-back, and every episode must show
  some reveal/promise/character-arc progress.
- **Persistence** - `SeasonPlanRecord` table, versioned (never overwritten -
  ADR-019): each regeneration inserts a new version; `get_current_plan`
  returns the latest *approved* version if one exists, else the latest
  version overall.
- **Closed-loop retry** - a `BLOCK` season plan triggers one regeneration
  with the validator's reasons fed back into the prompt (same pattern as the
  shot-plan retry), then persists whatever the final attempt produced.
- **Orchestrator integration** - `Showrunner.run()` now generates and
  persists the season plan between cast and episode-outline generation, and
  passes it into `EpisodeStage.generate_outlines` as binding context (an
  outline "MUST follow that episode's assigned act, reveals, promises and
  escalation level"). `PipelineResult` carries `season_plan_id`/
  `season_plan`/`season_qc`.
- **API** - `GET /series/{id}/season-plan` (current), `GET .../versions`,
  `GET .../{version}`, `POST .../regenerate`, `POST .../{version}/approve`.
- **Migration** - `alembic/versions/276af56e655b_add_season_plans.py`.

### Module 02 - Multi-Episode Engine

- **`EpisodeEngine`** (`pipeline/episode_engine.py`) extends generation from
  Episode-1-only to any episode: `generate_episode(project_id, series_id, n)`,
  `generate_next_unfinished(...)`, `generate_range(..., start, end)`.
  Workflow per episode: (already-approved outline) -> script -> shots (with
  the existing one-retry-on-BLOCK loop) -> retention/continuity QC -> canon
  commit only if neither gate BLOCKed. `Showrunner.run()` now delegates
  Episode 1 generation to this engine instead of duplicating the logic
  inline (`JobRunner`, extracted from the old `Showrunner._run_job`, is
  shared by both).
- **Bounded canon context** (`pipeline/canon_builder.py`) - builds each
  episode's `CanonSnapshot` from committed `CanonEvent` rows and prior
  *committed* episodes' outlines only (objective + cliffhanger), never from
  raw prior scripts. The `recap` field is explicitly convenience context;
  `locked_facts`/`character_summaries`/`unresolved_hooks`/`prior_events`
  are what continuity checks and prompts actually rely on.
- **Failed episodes never enter canon** - unchanged rule from XER-001,
  extended to every episode: `EpisodeGenerationStatus.QC_BLOCKED` episodes
  commit no `CanonEvent` rows, so episode N+1's canon snapshot cannot see
  anything from a rejected episode N.
- **Regeneration safety** - regenerating an already-`CANON_COMMITTED`
  episode retires (not deletes) its previous canon events
  (`EpisodeRepository.invalidate_canon_events`, `committed=False`) before
  recommitting fresh ones, and marks every *later* `CANON_COMMITTED`
  episode `STALE` (`_invalidate_downstream`) rather than silently leaving
  it built on canon that no longer holds. `Episode.version` increments each
  time a script is regenerated (lightweight "versioned reruns" signal; full
  script-history versioning was judged out of scope - see deviation below).
- **Resume** - `generate_next_unfinished` picks the lowest-numbered episode
  that is not yet `CANON_COMMITTED` (so a `QC_BLOCKED` episode is retried,
  not skipped), which is what "reopen/resume from database" means in
  practice for Trial 01 - see deviation note below.
- **API** - `POST /series/{id}/episodes/{n}/generate`,
  `POST .../generate-next`, `POST .../generate-range?start=&end=` (all take
  `project_id` as a query param for job attribution).
- **Migration** - `alembic/versions/a6445d655373_add_episode_version.py`
  (`episodes.version`).

### Module 03 - Director & Prompt Compiler

- **Extended Shot contract** (`domain/scene.py`) - added `blocking` (free
  text, deliberately not a coordinate system - "avoid overengineering
  spatial blocking V1"), `continuity_group` (adjacent shots that must
  generate sequentially and chain last->first frame, ADR-017), and
  `provider_requirements` (`ProviderRequirements`: text/image-to-video,
  first/last-frame, subject-reference, native-audio flags a future
  Module 07 router can filter providers on) - all optional/defaulted, no
  break to existing shot plans.
- **`DirectorValidator`** (`pipeline/director_validators.py`) - three
  deterministic, non-blocking production-readiness checks distinct from
  story QC: `check_vertical_composition` (missing framing/composition,
  crowded shots without a wide/full shot_size), `check_dialogue_coverage`
  (a multi-speaker scene needs at least one single/reaction shot, not only
  a continuous two-shot - research/WIND_COMIC_DEEP_DIVE.md section 7), and
  `check_continuity_grouping` (a `continuity_group` must be a contiguous
  shot run - BLOCK if not - and every shot but the group's last should set
  `last_frame_required`). Run for every shot-plan attempt in `EpisodeEngine`
  and persisted as `QualityReport` rows; they never gate canon commit
  (production readiness is a separate concern from narrative canon).
- **`PromptCompiler`** (`pipeline/prompt_compiler.py` +
  `domain/generation_request.py:ShotGenerationRequest`) - pure/deterministic
  compiler combining shot intent + Character DNA (formatted from
  `CharacterDNA` structured fields, falling back to `description`) + shot
  references + a stable default negative-constraint set into one
  provider-neutral request per shot. No vendor syntax anywhere in the
  domain model - see the module's "Do not put Runway/Kling/Veo/etc. syntax
  into domain models" instruction. Exposed via
  `GET /episodes/{id}/generation-requests` (compiled on demand, not
  persisted - it's a pure function of already-persisted data).
- **Migration** - `alembic/versions/42f264e2c041_add_shot_director_fields.py`
  (`shots.blocking`, `shots.continuity_group`, `shots.provider_requirements`).

### Module 04 - Asset & Storage System

- **`Asset` domain model** (`domain/asset.py`) - `AssetType` (image/video/
  audio/subtitle/document/other), `AssetStatus` (pending/accepted/rejected),
  `AssetOwnership` (`project_id` required; `series_id`/`episode_id`/
  `scene_number`/`shot_number` optional), `AssetProvenance` (provider/model/
  prompt_version/generation_params/source_reference_asset_ids/source_url) -
  every asset carries full lineage back to what produced it (ADR-020).
- **`StorageProvider` protocol + `LocalStorageProvider`**
  (`providers/storage.py`, `providers/local_storage.py`) - `save_bytes`/
  `save_file`/`read_bytes`/`exists`/`delete`/`list_all`/`absolute_path`, all
  routed through a path-traversal guard (`UnsafeStoragePathError` on any
  `../` or absolute-path escape from the storage root) and `asyncio.to_thread`
  for filesystem I/O. Root path is `Settings.asset_storage_path`
  (ADR-022 - local filesystem first, remote/S3-style providers implement the
  same protocol later without touching callers).
- **`AssetService`** (`services/asset_service.py`) - `ingest_bytes`/
  `ingest_file`/`ingest_from_url` sha256-hash the content, store it at
  `{hash[:2]}/{hash}{ext}` (content-addressed, so identical bytes are only
  ever written to disk once), but always create a *new* `Asset` row per
  ingestion call so per-event ownership/provenance/lineage is never merged
  away just because the bytes match something already stored. `accept`/
  `reject` transition status; `delete` refuses to remove an `ACCEPTED` asset
  unless `force=True`, and is dedup-safe - it only deletes the physical file
  once no other `Asset` row still references that `storage_path`.
  `find_missing_files`/`find_unreferenced_files` reconcile DB rows against
  what is actually on disk. `ingest_from_url` is the sanctioned way any
  future provider (image/video/audio) output becomes a durable asset instead
  of a transient provider URL (ADR-020's "never treat provider URLs as
  permanent").
- **Persistence** - `Asset` table (flattened ownership/columns, JSON
  `provenance`), `AssetRepository` protocol + SQLAlchemy implementation,
  following the same pattern as every other repository in this codebase.
- **API** (`api/routers/assets.py`) - `GET /assets` (filtered by
  project_id/series_id/episode_id/asset_type), `GET /assets/{id}`,
  `GET /assets/{id}/download`, `POST /assets/{id}/accept`,
  `POST /assets/{id}/reject?reason=`, `DELETE /assets/{id}?force=`,
  `POST /assets/upload` (multipart, for manual/reference assets - sets
  `provenance.provider = "manual_upload"`). `app.state.storage_provider` is
  built once in `lifespan` alongside the DB engine.
- **Migration** - `alembic/versions/4e20f6801cd1_add_assets_table.py`.
- Acceptance criterion met: any future provider output (image/video/audio
  bytes or a provider-hosted URL) can be handed to `AssetService.ingest_*`
  and immediately becomes a durable, traceable-lineage Xerama asset - no
  media provider integration exists yet to call it, but the contract and a
  fully working local-storage implementation are in place end to end
  (upload -> hash -> store -> accept/reject -> download -> delete),
  verified by 31 new tests (12 storage, 2 domain, 6 repository, 9 service,
  3 API - `find_missing_files`/`find_unreferenced_files`/dedup-safe-delete/
  path-traversal-rejection all directly exercised).

### Module 05 - Character Casting Studio

- **Extended `Character` identity fields** (`domain/character.py`) -
  `reference_pack` (multi-view: view name -> Asset id - front/three_quarter/
  side/full_body/expression_*, per playbook "Reference pack"),
  `identity_provenance` (`CharacterProvenance`), `locked`, `version`
  (lightweight counter, same precedent as `Episode.version` from Module 02 -
  full identity history was judged not worth the added state machine for
  Trial 01). `visual_identity_id`/`voice_identity_id`/`character_dna` were
  already in place from XER-001/ADR-012 and are reused as-is (not
  duplicated).
- **`CharacterProvenance`** - `identity_type` (`IdentityType`:
  `synthetic_original` | `licensed_authorized`), `consent_reference`,
  `notes`. There is deliberately no "unlicensed real person" value in
  `IdentityType`, so an unauthorized celebrity-cloning workflow has nothing
  to select - per "Do not implement unauthorized celebrity-cloning
  workflows." A `licensed_authorized` identity without a `consent_reference`
  fails Pydantic validation outright.
- **Lock/immutability** - `CharacterCastingService.update_identity`/
  `set_provenance` raise `PermissionError` while `character.locked` is
  `True` (playbook: "Never generate a recurring character from scratch once
  the identity is approved... immutable unless the character is
  deliberately recast"). `unlock_for_recast` is the one sanctioned way past
  a lock - it unlocks and increments `version` in the same operation, so a
  recast is always an explicit, auditable act. Wardrobe/physical-state
  variants are intentionally NOT blocked by a lock - new outfits/states are
  expected to accumulate over a season regardless of whether the
  character's face/body identity is frozen.
- **`WardrobeVariant` / `CharacterPhysicalStateVariant`** - versioned
  outfit/state assets per playbook "Wardrobe as assets" ("do not prompt
  'same clothes as before'"), each with its own `reference_asset_ids` list;
  added freely via `CharacterCastingService.add_wardrobe_variant` /
  `add_physical_state_variant`, independent of the parent character's lock
  state.
- **`ConsistencyPolicy`** (`services/consistency_policy.py`, ADR-014) - the
  one place that selects, per character per shot: root identity -> ordered
  reference-pack views -> wardrobe-variant references -> physical-state
  references, deduplicated and bounded by a per-provider
  `max_references` cap (`DEFAULT_MAX_REFERENCES_PER_CHARACTER = 4`,
  documented as a conservative placeholder until Module 07 exposes real
  per-provider limits). `select_for_shot` selects each character in a shot
  independently so one character's references never leak into another's.
  Falls back to the character's own id when no identity assets exist yet
  (pre-image-generation), preserving prior Module 03 behavior exactly.
  `PromptCompiler.compile_shot` (Module 03) now calls this instead of
  improvising `visual_identity_id or character.id` inline - closes the
  ADR-014 gap flagged when Module 03 shipped. `format_character_dna` was
  extracted from `PromptCompiler` into `domain/character.py` as a shared
  pure function so DNA-text phrasing can never drift between the compiler
  and the policy.
- **Identity-QC interface** (`providers/identity_qc.py`) - `IdentityQCProvider`
  Protocol (`score_identity(character, candidate_asset, reference_asset) ->
  QCResult`) plus placeholder pass/block thresholds
  (`IDENTITY_SIMILARITY_PASS_THRESHOLD = 7.0`,
  `IDENTITY_SIMILARITY_BLOCK_THRESHOLD = 5.0`), matching every other QC
  gate's pass/warn/block shape (ADR-018). No implementation - Module 05
  explicitly defers "multimodal implementation to Module 11" since real
  face/likeness comparison needs a vision model this module does not add.
- **`AssetOwnership.character_id`** - assets (root portraits, reference-pack
  views, wardrobe/physical-state photos) can now be attributed to a
  character independent of any episode/scene/shot; `AssetRepository.
  list_by_ownership`/`GET /assets`/`POST /assets/upload` all accept the new
  optional filter/field.
- **API** (`api/routers/characters.py`) - `GET /characters/{id}`,
  `POST /characters/{id}/lock`, `POST /characters/{id}/unlock` (recast),
  `PATCH /characters/{id}/identity`, `POST /characters/{id}/provenance`,
  `POST`/`GET /characters/{id}/wardrobe`,
  `POST`/`GET /characters/{id}/physical-states`. Identity endpoints return
  409 when the character is locked, 404 for an unknown character.
- **No `ImageProvider`/fake image provider added here** - Module 06 owns
  that contract ("Define `ImageProvider` contract and fake implementation");
  Module 05's identity assets are populated via Module 04's existing manual
  upload path (`POST /assets/upload`) for Trial 01, or later via Module 06's
  provider once it exists - see deviation note below.
- **Migration** - `alembic/versions/2baba9e0ec9a_add_character_casting_studio.py`
  (`characters.reference_pack/identity_provenance/locked/version`,
  `assets.character_id`, `character_wardrobe_variants`,
  `character_physical_state_variants`).
- Acceptance criterion met: a recurring character now has a durable
  identity package (root asset pointer, multi-view reference pack,
  Character DNA, wardrobe/physical-state variants, voice pointer, lock
  state, provenance/consent) that `ConsistencyPolicy` already compiles into
  every shot's `ShotGenerationRequest` today - downstream storyboard/image/
  video/audio stages (Modules 06/08/09) reference it through that one
  policy rather than each improvising their own selection - verified by 30
  new tests (6 domain, 6 repository, 6 service, 9 policy, 3 API) plus the
  full existing suite staying green with the `PromptCompiler` change.

### Module 06 - Style Bible, Storyboard & Image Production

- **`StyleBible`** (`domain/style_bible.py`, ADR-013) - one production-anchor
  row per series: `style_asset_id` (canonical image), `style_dna` (textual),
  `palette`, `lighting`, `texture`, `color_temperature`, `composition_rules`,
  `negatives`, plus `locked`/`version` using the exact same immutability
  pattern as `Character` (Module 05) - `StyleBibleService.update` raises
  `PermissionError` while locked; `unlock_for_recast` is the sanctioned way
  past a lock and bumps `version`. Deliberately not a versioned-history
  table (unlike `SeasonPlanRecord`) - a Style Bible is a single anchor, not
  a sequence of drafts under review.
- **`Storyboard`** (`domain/storyboard.py`) - one per-shot workflow record
  (`draft`/`approved` + `approved_keyframe_asset_id`). Individual keyframe
  attempts are NOT a new entity - they are plain `Asset` rows (Module 04,
  `type=image`, `ownership.scene_number/shot_number`, `take_number`),
  reusing Module 04's accept/reject/dedup machinery completely rather than
  duplicating an asset-like "Keyframe" model.
- **`ImageProvider` contract + `FakeImageProvider`**
  (`providers/image.py`, `providers/fake_image.py`) - `ImageProviderCapabilities`
  (`supports_reference_images`, `max_reference_images`, `supports_edit`,
  `supports_mask`, `supported_aspects`, `priority`, `estimated_cost_usd`)
  per research/PRODUCTION_STACK_2026.md "Provider contract". No paid/free
  real provider is wired up - `app.state.image_provider` is a
  `FakeImageProvider` (mirrors `FakeLLMProvider`'s scripted-queue pattern);
  manual upload (Module 04's ingest path) is the first-class fallback.
- **`StoryboardService`** (`services/storyboard_service.py`) -
  `generate_keyframe` rejects an incompatible provider (unsupported aspect
  ratio, or references requested but unsupported) with
  `UnsupportedProviderCapabilityError` *before* calling `ImageProvider.generate`
  (per the research doc: "reject an incompatible provider before spending a
  generation request"); resolves each compiled reference id to actual bytes
  via `AssetService`, skipping any that don't resolve to a real asset yet
  (pre-image-generation Character-DNA-only fallback); ingests the result as
  a take-numbered `Asset`. `accept_keyframe`/`reject_keyframe` delegate to
  `AssetService.accept`/`reject`; a rejection leaves the storyboard `draft`
  so the next `generate_keyframe`/`upload_keyframe` call is the retry, with
  `take_number` incrementing each time (never overwritten - ADR-019).
  `upload_keyframe` is the same manual-upload fallback, first-class per the
  module spec.
- **Style Bible now actually flows into compiled prompts** - `PromptCompiler.
  compile_shot`/`compile_episode` (Module 03) take an optional `StyleBible`:
  `style_dna` populates `ShotGenerationRequest.style_dna`, `style_asset_id`
  fills `references.style_asset_id` (a shot-level override still wins if the
  Director set one), and `negatives` are appended to the negative-constraint
  set. This closes the Module 03 deviation note ("`style_dna` is always ""
  for now") now that a real Style Bible exists.
  `GET /episodes/{id}/generation-requests` now fetches/creates the series'
  Style Bible and passes it through.
- **`AssetRepository.list_by_ownership`** gained `scene_number`/
  `shot_number` filters (alongside Module 05's `character_id`) so a
  storyboard's keyframe takes can be queried precisely; exposed on
  `GET /assets` too.
- **API** - `GET/PATCH /series/{id}/style-bible`, `POST .../lock`,
  `POST .../unlock`; `POST /episodes/{id}/scenes/{n}/shots/{n}/storyboard`
  (idempotent get-or-create), `GET /episodes/{id}/storyboards`,
  `GET /storyboards/{id}`, `POST /storyboards/{id}/keyframes/generate`,
  `POST .../keyframes/upload` (multipart), `GET .../keyframes`,
  `POST .../keyframes/{asset_id}/accept`, `POST .../keyframes/{asset_id}/reject`.
- **Migration** - `alembic/versions/c9737e7a2af4_add_style_bible_and_storyboards.py`
  (`style_bibles`, `storyboards` tables).
- Acceptance criterion met: `POST /storyboards/{id}/keyframes/generate` (or
  `/upload` when no provider is available) plus `/accept` takes a shot from
  "approved in the shot plan" to "durable, take-numbered, character/style/
  location-referenced key frame asset with an audit trail of every rejected
  attempt" - verified end-to-end in the API test suite (generate -> list ->
  accept, and reject -> still-draft -> manual-upload retry with an
  incremented take number) plus 32 new unit tests (style bible domain/
  repository/service lock-immutability, storyboard repository CRUD/
  idempotency, fake image provider, storyboard service capability
  rejection/take-numbering/accept-reject, and Style-Bible-into-PromptCompiler
  integration).

## Partially implemented

- **Character/Style identity** - the full structural layer (`Character`,
  `CharacterDNA`, `reference_pack`, `StyleBible`, lock/version, wardrobe/
  physical-state variants) exists per ADR-012/013 and a `FakeImageProvider`
  can populate it end to end for tests, but no *real, credentialed* image
  provider is wired up yet, so in a real run these fields stay populated by
  manual upload / LLM text only until a real `ImageProvider` (paid or a
  practical free/trial API) is added.
- **Provider health** - `ProviderHealthTracker` exists and is used by the AI
  gateway, but there is only one provider (OpenRouter) so there is no
  fallback *across* providers yet, only a circuit-break signal.
- **Jobs** - modeled with the required states and used for every pipeline
  stage, but execution is synchronous within the HTTP request (per
  docs/ARCHITECTURE.md section 14, this is explicitly acceptable for Trial
  01: "a simple SQLite-backed local worker is acceptable"). No background
  worker/queue process exists yet.

## Planned (not started)

- Video/voice/lip-sync provider adapters, media provider router, FFmpeg
  assembly (Modules 07-09/12).
- Analytics/learning feedback loop (Phase 5).
- PostgreSQL/S3 adapters (repository/storage interfaces are ready for this;
  no concrete implementation exists yet - ADR-021/ADR-022).
- See `modules/README.md` for the full remaining module list (07-14).
- `Showrunner.run()` still auto-generates only Episode 1 end-to-end (by
  design - see deviation below); episodes 2..N require an explicit
  `EpisodeEngine` call (API or code).

## Blocked

None. No architectural blocker was found; docs/research were internally
consistent enough to start coding per
`research/CODING_READINESS_CHECKLIST.md`.

## Documented deviations / conflict resolutions

1. **SeriesBible field set** - `docs/JSON_CONTRACTS.md`'s SeriesBible JSON
   schema and `docs/DATA_MODEL.md`'s prose field list for "Series Bible" only
   partially overlap (DATA_MODEL.md has `premise`, `protagonist_objective`,
   `primary_opposition`, `prohibited_contradictions`; JSON_CONTRACTS.md does
   not). `xerama/domain/story.py:SeriesBible` is the union of both rather
   than a strict pick of one - see the docstring there.
2. **AI-call telemetry is disabled for this build**, per explicit project
   direction during this coding session (overriding docs/ARCHITECTURE.md
   section 15 and ADR-010, which call per-call telemetry "extremely
   important"). No `GenerationRecord`/`AICallRecord` table or
   `TelemetryRecorder` service exists; the AI gateway logs retries via
   standard logging only. `GenerationJob` (stage-level state/timestamps/
   error) still exists and is unaffected - that is a separate ADR-023
   requirement, not telemetry. Re-adding per-call telemetry is a small,
   additive change if/when requested again (the gateway already has one
   choke point - `AIGateway.generate` - where it would hook in).
3. **Canon change classification is a keyword heuristic, not an LLM call** -
   `pipeline/canon_commit.py:classify_change_type` guesses a
   `CanonChangeType` from the outline's free-text `canon_changes` strings.
   Nothing downstream currently branches on that type, so a
   misclassification is a soft/cosmetic issue (the original description is
   always preserved) rather than a correctness bug. Revisit with an LLM
   classification call if/when a consumer starts relying on `change_type`.
4. **"Unresolved end-state" check (Module 01)** - `modules/01_SEASON_REVEAL_ENGINE.md`
   doesn't define what this validation means. Implemented as: (a) BLOCK if a
   thread is marked `resolved` without recording the episode it resolved in,
   or if a resolution/payoff episode falls outside the season (data
   integrity); (b) WARN if literally every mystery/promise resolves within
   the season, since docs/STORY_FORMULA.md's closing principle is to
   "optimize for continuation" - a fully-closed season is fine for a
   deliberate finale but should not happen by accident.
5. **Model-role -> stage mapping** - the roadmap/AI_MODELS.md role table
   doesn't say which role owns "series bible", "characters", "season plan" or
   "episode outlines" specifically. This implementation assigns all of them
   to `story_architect` (series/season structure, per its stated
   responsibility), reserves `episode_writer` for episode script prose only,
   and reuses `story_architect` for MERGE-decision concept synthesis (no
   dedicated "concept merger" role exists in the docs).
6. **Scope choices in Module 02** - `modules/02_MULTI_EPISODE_ENGINE.md`
   leaves several implementation details open:
   - **"Resume after failure"** is implemented at the *episode* granularity,
     not mid-episode: `generate_next_unfinished` restarts a `QC_BLOCKED`
     episode from its script rather than checkpointing after the script
     succeeded but shots failed. Full episode regeneration is cheap enough
     (2 LLM calls) that finer-grained resume was judged not worth the
     added state machine for Trial 01.
   - **"Versioned reruns"** is a lightweight `Episode.version` counter, not
     a kept history of every past script/shot-plan body (unlike
     `ConceptCandidateRecord` or `SeasonPlanRecord`, which do keep every
     version). `QualityReport` rows already preserve the per-attempt score/
     reasons audit trail for every take, which was judged sufficient
     evidence without also storing full superseded script text. Revisit if
     a future module needs to diff/restore a specific past episode script.
   - **`Showrunner.run()` still only auto-generates Episode 1** end-to-end;
     it does not loop `EpisodeEngine` over the full season automatically.
     This preserves the existing XER-001 "first end-to-end test" contract
     (docs/README.md's target pipeline description and existing
     `POST /generate-series` semantics) rather than silently turning one
     API call into N sequential LLM-heavy episode generations. Episodes
     2..N are one explicit call away (`generate-next`/`generate-range`).
7. **Scope choices in Module 05** - `modules/05_CHARACTER_CASTING_STUDIO.md`
   leaves several implementation details open:
   - **What "locked" protects** - the module says identity is "immutable"
     once approved but doesn't say whether that covers wardrobe/physical-
     state variants too. Implemented as: locking freezes only root-identity
     fields (`visual_identity_id`, `reference_pack`, `character_dna`,
     `identity_provenance`); wardrobe/physical-state variants can always be
     added, since new outfits/states are an expected, ongoing part of
     production regardless of whether the character's face/body is frozen
     (see playbook's separate "Wardrobe State"/"Physical State" branches
     under a single immutable "Root Identity").
   - **"Versioning"** is a lightweight `Character.version` counter bumped
     only on an explicit `unlock_for_recast` call, not a kept history of
     every past identity field value - the same precedent as
     `Episode.version` (deviation 6). `QualityReport`-style per-attempt
     history is left to Module 11's identity-QC retry loop, which will have
     actual candidate assets to attach a history to.
   - **No `ImageProvider`/fake image provider was added in this module** -
     `modules/06_STYLE_STORYBOARD_IMAGE.md` explicitly owns "Define
     `ImageProvider` contract and fake implementation," so Module 05 uses
     Module 04's existing manual-upload path to populate identity assets
     for Trial 01 rather than pre-empting Module 06's contract.
8. **Scope choices in Module 06** - `modules/06_STYLE_STORYBOARD_IMAGE.md`
   leaves several implementation details open:
   - **"Storyboard/keyframe records"** were implemented as one lightweight
     `Storyboard` workflow row per shot (status + approved-keyframe
     pointer) plus plain `Asset` rows for every keyframe take, rather than a
     new "Keyframe" entity duplicating what `Asset` (Module 04) already
     provides (content hash, accept/reject, take_number, provenance). A
     Keyframe *is* an Asset with `type=image` and shot-level ownership.
   - **Rough storyboard/layout step** is a single free-text
     `layout_description` field on `Storyboard`, not a separate
     geometry/sketch asset - matching Module 03's "avoid overengineering"
     precedent (deviation not to add a coordinate system for `blocking`).
   - **No real (paid/free) `ImageProvider` implementation** - the module
     spec says a real provider "may be added only if a practical free/trial
     API is available," and none was available/credentialed in this
     session, so only `FakeImageProvider` + manual upload exist. Swapping
     in a real provider later requires no interface change - just a new
     class satisfying `ImageProvider` and an `app.state.image_provider`
     wiring change.
