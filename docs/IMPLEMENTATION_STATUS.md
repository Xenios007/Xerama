# Xerama Implementation Status

_Last updated: 2026-08-25 - MODULE-037/038 (Music Engine, Sound Effects)._

**Numbering note:** `modules/` was restructured from 14 broad briefs
(`01_*.md`-`14_*.md`, now legacy/history-only) into the authoritative
`modules/MODULE-001_*.md`-`MODULE-080_*.md` queue (see
`modules/README.md` and `docs/ARCHITECTURE_FREEZE_001_080.md`). Sections
below titled "Module NN" predate the restructure; sections titled
"MODULE-NNN" use the new queue. Nothing was rebuilt for the rename - the
new queue's own rule is "inspect and reuse... do not reimplement working
functionality merely to match filenames."

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
- **Tests** - 344 tests (see `tests/`), all against `FakeLLMProvider` /
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

### Module 07 - Media Provider Registry & Router

- **`VideoProvider`/`VoiceProvider`/`LipSyncProvider` contracts**
  (`providers/video.py`, `providers/voice.py`, `providers/lip_sync.py`) -
  capability metadata per research/PRODUCTION_STACK_2026.md's video/voice/
  lip-sync provider contract sections, plus a `FakeVideoProvider`/
  `FakeVoiceProvider`/`FakeLipSyncProvider` for each (same scripted-queue
  pattern as `FakeLLMProvider`/`FakeImageProvider` - can return bytes or
  raise a queued `ProviderError`). `providers/video.py:matches_requirements`
  is the eligibility filter between a shot's `ProviderRequirements`
  (Module 03 - "declared here so the Module 07 router can filter eligible
  providers without the Director knowing vendor names") and a video
  provider's capabilities - the integration point Module 03 was built for.
  `ImageProvider`/`FakeImageProvider` (Module 06) needed no contract
  changes - it already matched the shape - but gained `ProviderError`
  support in its queue and a configurable `name` (needed for router
  fallback tests with multiple registered providers).
- **`MediaProviderRouter`** (`services/media_router.py`) - one generic
  router (not four copies) over any provider type exposing `.name` and
  `.capabilities.priority`: capability filter (caller-supplied predicate,
  since image/video/voice/lip-sync capability shapes all differ) -> health
  filter (`ProviderHealthTracker`, reused as-is - ADR-011) -> priority
  order (deterministic: higher `priority` first, stable tie-break on
  registration order) -> attempt -> on `ProviderError`, record the failure
  into the health tracker, log the reason as a `RoutingAttempt`, and try
  the next eligible provider. Raises `NoEligibleProviderError` (carrying
  every attempt's outcome) only once every eligible provider has been
  tried. Reuses `ProviderError`/`classify_status_code`/`ProviderHealthTracker`
  exactly as documented in their own docstrings ("and future media
  providers") - no second error/health system was built.
- **`pipeline/ai_gateway.py` (OpenRouter LLM path) is untouched** - the
  module spec says "Preserve current OpenRouter behavior"; `AIGateway`
  still retries the same single provider rather than falling back across
  registered ones, which is a deliberate difference from
  `MediaProviderRouter` (LLM routing/fallback across multiple providers
  was never in scope here - only media generation).
- **Module 06 upgraded to route through the registry** -
  `StoryboardService.generate_keyframe` now takes a
  `MediaProviderRouter[ImageProvider]` instead of a single injected
  provider, so an image keyframe request asks for capabilities (aspect
  ratio, reference-image support) and the router picks/falls back among
  every registered image provider - the old `UnsupportedProviderCapabilityError`
  (single-provider, pre-call rejection) is now `NoEligibleProviderError`
  (multi-provider, tried-and-none-worked). Every accepted/attempted
  provider's routing attempts are recorded in the resulting Asset's
  `provenance.generation_params["routing_attempts"]` for audit.
- **App wiring** - `app.state.image_router`/`video_router`/`voice_router`/
  `lip_sync_router` are each a `MediaProviderRouter` seeded with one fake
  provider (no real credentialed adapter is available in this
  environment); `video_router`/`voice_router`/`lip_sync_router` exist as
  registries ready for Modules 08/09 to consume - no endpoint calls them
  yet, since actual video/audio production workflows are those modules'
  job, not this one's.
- Acceptance criterion met: a caller (`StoryboardService`, and any future
  Module 08/09 caller) asks a `MediaProviderRouter` for a capability via an
  `is_compatible` predicate, never names a vendor - verified by 20 new
  tests (deterministic priority ordering incl. stable tie-break, capability
  filtering, health-circuit skip, fallback-after-failure with health
  recorded, exhausted-fallback error, fake video/voice/lip-sync provider
  round trips, and `matches_requirements`'s aspect/duration/first-last-
  frame/subject-reference/native-audio checks) plus the full existing
  suite staying green through the `StoryboardService` refactor.

### MODULE-032 - Video Generation (formerly Module 08 - Video Production)

- **`ShotVideoProduction`** (`domain/video_production.py`) - one per-shot
  workflow record (draft/approved + `approved_take_asset_id` +
  `extracted_last_frame_asset_id`), mirroring `Storyboard`'s pattern
  exactly. Video takes are plain `Asset` rows (`type=video`, `take_number`)
  - no duplicated asset-like entity, same principle as Module 06's
  keyframes.
- **`VideoProductionService`** (`services/video_production_service.py`) -
  `generate_take` resolves compiled shot references to bytes, asks a
  `MediaProviderRouter[VideoProvider]` for a capability-eligible/healthy
  provider (falling back across registered video providers on failure -
  Module 07's router, reused as-is), and ingests the result as a
  take-numbered video `Asset`. `upload_take` is the manual-upload fallback.
  `accept_take`/`reject_take` delegate to `AssetService` (never overwrites
  a take - ADR-019; a rejection leaves the production `draft` for retry).
- **Continuity sequencing** (ADR-017, research/PRODUCTION_STACK_2026.md
  "Previous-frame continuity") - shots sharing a `continuity_group` must
  generate in order: `generate_take` looks up the immediately preceding
  shot's `ShotVideoProduction` (by `(scene_number, shot_number)` within the
  group) and raises `ContinuityOrderingError` *before* calling any
  provider if that predecessor hasn't been accepted-and-extracted yet.
  Once accepted, `accept_take` extracts the take's actual last frame (via
  `FrameExtractor`) and records it as `extracted_last_frame_asset_id` -
  that real final frame (not the original storyboard keyframe) becomes the
  next shot's `first_frame` input, exactly matching the playbook's guidance
  that the actual generated frame is a better continuity anchor than the
  plan. Standalone shots (no `continuity_group`) never trigger extraction.
  Independent shots have no ordering constraint and can generate/retry in
  any order or concurrently.
- **No cascading invalidation** - a rejected/failed take never touches any
  other shot's production record or takes (unlike episode/canon
  regeneration in Module 02, a deliberately different concern). Satisfies
  "Failed shots must not force regeneration of successful shots."
- **`FrameExtractor` contract** (`providers/frame_extractor.py`) -
  `FFmpegFrameExtractor` (real, shells out to `ffmpeg -sseof -1 ...`, not
  exercised by tests since no `ffmpeg` binary is assumed installed) and
  `FakeFrameExtractor` (deterministic placeholder, what tests actually run
  against - "Use fake provider for tests"). `app.state.frame_extractor`
  auto-selects the real extractor only if `ffmpeg` is found on `PATH`
  (`shutil.which`), else falls back to the fake one - same "optional real
  adapter" principle as every media provider.
- **`AssetService.ingest_bytes`/`ingest_file`/`ingest_from_url` gained
  `width`/`height`/`duration_seconds`** (Module 04 gap-fill) - these
  fields already existed on `Asset`/`AssetRepository.create` but were
  never exposed through the convenience ingest methods until a video take
  actually needed to record its duration.
- **API** (`api/routers/video_production.py`) -
  `POST /episodes/{id}/scenes/{n}/shots/{n}/video-production` (idempotent;
  `continuity_group` read from the approved shot plan, not client-supplied,
  so sequencing always matches the Director's actual data),
  `GET /episodes/{id}/video-productions`, `GET /video-productions/{id}`,
  `POST /video-productions/{id}/takes/generate` (uses the shot's approved
  Storyboard keyframe as `first_frame` when one exists),
  `POST .../takes/upload`, `GET .../takes`,
  `POST .../takes/{asset_id}/accept|reject`. `NoEligibleProviderError` ->
  422, `ContinuityOrderingError` -> 409. Shared shot/episode-lookup logic
  extracted to `api/shot_lookup.py` (was duplicated inline in
  `storyboards.py`; both routers now import it - "reuse existing
  components instead of duplicating them").
- **Migration** - `alembic/versions/8fe8803fbf26_add_shot_video_productions.py`.
- Acceptance criterion met: given an approved keyframe, `POST .../takes/generate`
  (or `/upload`) through `/accept` produces a durable, take-numbered video
  asset with traceable lineage and continuity metadata using
  `FakeVideoProvider`/`FakeFrameExtractor` end to end - verified by 22 new
  tests (frame-extractor unit tests, video-production repository CRUD +
  continuity-predecessor lookup, service take-numbering/capability-
  rejection/continuity-ordering-enforcement/continuity-chaining/resume-
  after-predecessor-accepted/reject-retry/manual-upload, and end-to-end API
  generate/accept and reject/manual-upload-retry coverage) plus the full
  existing suite staying green.

### MODULE-001 / MODULE-002 audit - Core Platform Architecture, Configuration & Environment

- **Architecture-boundary audit** (MODULE-001) - found and fixed one real
  violation: `domain/asset.py` imported `xerama.db.base.utcnow`, directly
  contradicting `db/base.py`'s own documented boundary ("Domain and
  pipeline code must never import this module directly"). Replaced with a
  private `_utcnow()` helper local to `domain/asset.py` - no other
  `domain/` module imports `db`/`api`/`repositories`/`providers`/
  `pipeline`/`services`. Added `tests/test_architecture_boundaries.py`
  (static text scan of every `domain/*.py` import line) so this class of
  regression fails CI instead of needing to be rediscovered by audit.
  Everything else audited under MODULE-001 (package layout, service/
  repository/provider boundaries, application bootstrap) was already
  sound - no other changes needed.
- **Secret handling** (MODULE-002) - `Settings.openrouter_api_key` is now
  `pydantic.SecretStr` instead of a plain `str`, so it can never leak
  through a log line, `repr()`, or an accidental `str()` of the settings
  object; call sites (`api/app.py`, `cli.py`) now call
  `.get_secret_value()` explicitly at the one point they construct
  `OpenRouterProvider`. `.env.example` already existed with placeholders
  only (verified, no change needed).
- **`ffmpeg_path` setting added** - Module 08/MODULE-032's
  `FFmpegFrameExtractor` previously hardcoded the binary name `"ffmpeg"`;
  it's now `Settings.ffmpeg_path` (env `FFMPEG_PATH`, default `"ffmpeg"`),
  closing the "Centralize... FFmpeg... settings" requirement. Worker and
  frontend/CORS settings are intentionally not added yet - no job
  worker (MODULE-041/042) or frontend (MODULE-055+) exists to configure.
- **`tests/test_config.py`** (new) - defaults, env-var override, secret
  redaction (`repr`/`str` never contain the raw key), and
  `ModelRoleRegistry` free-default-fallback/explicit-override coverage -
  the exact test categories MODULE-002 asks for.
- Both modules were AUDIT/EXTEND, not BUILD - no new subsystem was added;
  existing config/architecture were already ~95% compliant, one real gap
  found and closed per audit, verified by 6 new tests plus the full
  existing suite staying green.

### MODULE-003 through MODULE-021/023 audit summary

Audited against the existing implementation (XER-001 baseline + old
Modules 01-03): domain contract system, database/persistence, repository
architecture, AI gateway, model registry/routing, provider health,
creative brief, concept generation, judge/merge, series bible, canon/
memory, season architecture, reveal/mystery engine, episode planning,
script generation, continuity engine, story quality engine, director
engine, and shot planning are all already substantially implemented and
tested from earlier work in this session (see the XER-001 and "Module
01/02/03" sections above) - no rebuild needed, matching the new queue's
own rule. Specific items double-checked directly rather than assumed:
`SeriesBible.locked_facts` already distinguishes locked vs. editable
facts (MODULE-012); `.env.example` already has placeholders only
(MODULE-002, verified above). MODULE-022 (Scene Blocking) was the first
genuine gap found in this range - see below. Two small deferred items
worth naming rather than silently skipping: `aspect_ratio` fields have no
explicit format validation yet (low-risk - nothing currently sets them to
an invalid value), and `AIGateway` has no explicit cancellation-token
API (Python task cancellation already propagates through its `await`
points, so this is judged already-adequate rather than a gap).

### MODULE-022 - Scene Blocking

- **`CharacterBlock`/`MovementBeat`/`SceneBlocking`** (`domain/scene.py`,
  `ScreenPosition`/`BlockingDepth` enums in `domain/enums.py`) - lightweight
  left/center/right + foreground/midground/background positions (not real
  coordinates - "keep schema extensible to coordinates later"), visible/
  speaking/reacting flags, `occluded_by` character-id list, and a
  `screen_direction` string per shot for continuity checks. Added as
  `Shot.blocking_plan: SceneBlocking | None = None` - optional and
  additive alongside the existing free-text `Shot.blocking`, which stays
  exactly as it was (no shot plan anywhere needs to change to keep
  working).
- **`DirectorValidator.check_scene_blocking`** (`pipeline/director_validators.py`)
  - BLOCK if a shot's `blocking_plan` is set but missing a `CharacterBlock`
  for one of `shot.character_ids` (data-integrity violation, same
  precedent as `check_continuity_grouping`'s non-contiguous-group BLOCK);
  WARN if two visible characters share the same position+depth without
  one listing the other in `occluded_by` ("validate multi-character
  blocking"); WARN if shots in the same `continuity_group` disagree on
  `screen_direction` ("preserve screen direction across connected
  shots"). Shots with no `blocking_plan` are skipped entirely - the
  structured plan is opt-in. Wired into `EpisodeEngine`'s existing
  Director-QC pass alongside the other three checks (persisted as a
  `QualityReport`, informational only - never gates canon commit, same as
  the other Director checks).
- **Persistence** - `shots.blocking_plan` JSON column
  (`alembic/versions/25a65ab303cb_add_shot_blocking_plan.py`); nullable,
  so every existing/fixture shot plan (none of which set it) round-trips
  unchanged.
- Acceptance criterion met: shot planning can now reason about spatial
  continuity (who's visible/speaking/reacting/occluding, and whether the
  established screen direction holds across a continuity group) without a
  full 3D engine - verified by 9 new tests (domain defaults/JSON round-
  trip, all three validator outcomes, repository round-trip) plus the
  full existing suite staying green.

### MODULE-029 audit / MODULE-030 - Image Generation, Image Editing & Regeneration

- **MODULE-029 (Image Generation) audit** - already fully satisfied by
  Module 06/07's `ImageProvider` contract + `FakeImageProvider` +
  `StoryboardService.generate_keyframe` (reference images, aspect ratio,
  per-take provider/prompt lineage via `AssetProvenance`, immediate
  persistence, retry/rejection). "Run image QC before marking accepted"
  is correctly out of scope here - MODULE-029 doesn't depend on
  MODULE-044 (Multimodal QC, not yet built); QC gating arrives with that
  module, same deferral already used for identity QC (Module 05).
- **`ImageEditRequest` + `ImageProvider.edit`** (`providers/image.py`) -
  provider-supported edit/mask path, only ever routed to a provider whose
  `capabilities.supports_edit` is `True` (and `supports_mask` when a mask
  is supplied) - the `MediaProviderRouter`'s capability filter keeps
  incompatible providers out of the pool before `.edit()` is called, same
  pattern as every other capability-gated call in this codebase.
  `FakeImageProvider.edit` added (default capabilities still have
  `supports_edit=False`, matching "not every provider supports this").
- **`StoryboardService.edit_keyframe`** - resolves the base take (and
  optional mask) to bytes, routes through `MediaProviderRouter`, and
  always ingests the result as a **new** take (`take_number` incremented,
  `source_reference_asset_ids=[base_asset_id, mask_asset_id?]`,
  `generation_params={"edit": True, "based_on_take": ...}`) - the base
  take's row is never touched, so "never overwrite accepted assets
  silently" holds structurally, not just by convention. "Strengthen
  references or change provider based on QC recommendation" needs no new
  mechanism: the caller can already pass a different/larger reference set
  into `generate_keyframe` (Module 05's `ConsistencyPolicy` already
  selects references) or let the router's existing fallback try another
  provider - both compose from what already exists.
- **API** - `POST /storyboards/{id}/keyframes/edit` (body: `instruction`,
  `base_asset_id`, optional `mask_asset_id`/`negative_prompt`/
  `aspect_ratio`). 422 on `NoEligibleProviderError`, 404 if
  `base_asset_id`/`mask_asset_id` don't resolve to a real asset row, 410
  if the row exists but its backing file is missing.
- No migration needed - edits reuse the existing `Asset`/take-numbering
  machinery from Module 04, nothing new to persist.
- Acceptance criterion met: a failed still can be repaired via a targeted
  edit (or, as before, a full regenerate via another `generate_keyframe`
  call) without touching any other shot's assets, with an auditable
  before/after lineage - verified by 10 new tests (fake-provider edit
  round trip/mask tracking/default capabilities, service edit lineage/
  base-take-untouched/capability-and-mask rejection, end-to-end API edit
  flow and unsupported-provider rejection).

### MODULE-033 - Character Motion / Performance

- **`MicroBeat` extended** (`domain/scene.py`) - `character_id`, `pose`,
  `expression`, `gaze`, `camera_note` added alongside the existing
  `start_seconds`/`end_seconds`/`description`, all optional/defaulted so
  every existing micro-beat (prose-only) keeps working unchanged. No
  migration needed - `shots.micro_beats` was already a JSON column.
  "Keep dialogue performance linked to speaker/emotion" is satisfied by
  construction: `character_id` ties a structured beat to a specific
  speaker, and `expression` carries the emotional beat.
- **`DirectorValidator.check_motion_plan`** - BLOCK on an inverted beat
  range (`start_seconds >= end_seconds`) or a beat extending past
  `shot.duration_seconds` (literally impossible timing); BLOCK on two
  beats for the *same* `character_id` overlapping in time (an impossible
  simultaneous pose/expression/gaze - beats for *different* characters
  are allowed to overlap, e.g. speaker + reaction); WARN when a shot
  averages more than one micro-beat per second (an overloaded plan a
  provider is unlikely to render faithfully). Wired into `EpisodeEngine`'s
  existing Director-QC pass alongside the other four checks.
- **"Provider capability differences for performance/subject reference"**
  needed no new code - already handled by `ProviderRequirements`/
  `VideoProviderCapabilities.subject_reference` and
  `providers/video.py:matches_requirements` (Module 07/08).
- Acceptance criterion met: motion is now structured, validated
  production data (character/pose/expression/gaze/timing) rather than one
  unbounded prose sentence, with impossible or overloaded plans caught
  before generation - verified by 9 new tests (domain defaults/round-trip,
  all `check_motion_plan` outcomes: valid/BLOCK-past-duration/BLOCK-
  inverted-range/BLOCK-same-character-overlap/PASS-different-character-
  overlap/WARN-overloaded-density) plus the full existing suite staying
  green.

### MODULE-034 / MODULE-035 - Voice Generation, Dialogue / Audio Pipeline

- **`VoiceProfile`** (`domain/voice.py`) - one row per character (mirrors
  `StyleBible`'s one-per-owner pattern): `provider`/`provider_voice_id`,
  `language`, `style`, `pronunciation_dictionary`, and `provenance` -
  **reuses `CharacterProvenance` from Module 05 directly** rather than
  duplicating an almost-identical rights/consent model, so "never assume
  cloning rights; provenance is required for external likeness/voice" is
  enforced by the exact same Pydantic validator that already blocks an
  unlicensed `identity_type=licensed_authorized` face. `locked`/`version`
  follow the same lock/recast pattern as `StyleBibleService`/
  `CharacterCastingService` - `VoiceProfileService.update` raises
  `PermissionError` while locked.
- **`ShotAudioProduction`** (`domain/audio_production.py`) - the same
  lightweight per-shot workflow record pattern as `Storyboard`/
  `ShotVideoProduction`, with `audio_mode` (native/tts_lipsync/hybrid,
  Module 03's existing `Shot.audio_mode`) copied in at creation.
  Individual dialogue takes are plain `Asset` rows (`type=audio`,
  `take_number`) - no duplicated entity.
- **`AudioProductionService.generate_dialogue_take`** - resolves the
  character's `VoiceProfile`, routes through
  `MediaProviderRouter[VoiceProvider]` (capability filter: profile
  language must be in the provider's `languages`, text length within
  `max_characters` - Module 07's router, reused as-is), and ingests a
  take-numbered `Asset` with `generation_params` recording
  `character_id`/`language`/`audio_mode`/routing attempts. For `native`
  mode the dialogue audio is the video provider's own output track and
  this service is intentionally not invoked; `hybrid` means this
  controlled dialogue layer is later mixed with native ambience by the
  deterministic editor (Module 12/MODULE-046), not here.
  `upload_dialogue_take`/`accept_take`/`reject_take`/`list_takes` mirror
  every other production service in this codebase.
- **API** - `GET/PATCH /characters/{id}/voice-profile`,
  `POST .../lock|/unlock`;
  `POST /episodes/{id}/scenes/{n}/shots/{n}/audio-production` (idempotent;
  `audio_mode` read from the approved shot plan, not client-supplied),
  `GET /episodes/{id}/audio-productions`, `GET /audio-productions/{id}`,
  `POST /audio-productions/{id}/takes/generate` (`character_id` + optional
  `text` - defaults to the shot's own scripted `dialogue`),
  `POST .../takes/upload`, `GET .../takes`,
  `POST .../takes/{asset_id}/accept|reject`.
- **Migration** - `alembic/versions/d3f28dc36975_add_voice_profiles_and_shot_audio_.py`
  (`voice_profiles`, `shot_audio_productions`).
- Acceptance criterion met: dialogue audio can be regenerated
  independently of video while retaining character voice identity (a
  `VoiceProfile` persists across takes and episodes; `generate_dialogue_take`
  never touches video/keyframe assets) - verified by 21 new tests (voice
  profile domain/repository/service lock-immutability, audio production
  repository CRUD, service take-numbering/capability-rejection
  (language/length)/accept-reject-retry, and end-to-end API coverage).
- **MODULE-040 (Media Asset Storage) audit** - already fully satisfied by
  Module 04's `StorageProvider`/`LocalStorageProvider` + `Asset`/
  `AssetService` (content hash, MIME/size/path, full lineage via
  `AssetProvenance`, project/series/episode/character/scene/shot
  ownership, take/version numbering, accept/reject status). No changes
  needed.

### MODULE-036 - Lip Sync

- **`VideoProductionService.generate_lip_synced_take`** - deliberately
  reuses the existing `ShotVideoProduction` record and take-numbering
  instead of a fourth parallel workflow table (Storyboard/
  VideoProduction/AudioProduction already exist): a lip-synced clip is
  just another way to produce a video take for a shot. Reads the source
  video take and a dialogue take (MODULE-034/035) as bytes, routes
  through `MediaProviderRouter[LipSyncProvider]` (capability filter:
  `aspect_ratio` supported and `duration_seconds <= max_duration_seconds`
  - Module 07's router, reused as-is), and always ingests the result as a
  **new** take - neither source asset is ever mutated, so "route failures
  to retry/QC without corrupting originals" holds structurally.
- **`_validate_lip_sync_eligibility` / `LipSyncEligibilityError`** -
  "validate visible speaker" without real face detection: when a
  `character_id` and the shot's MODULE-022 `SceneBlocking` are both
  supplied and that character's `CharacterBlock.visible` is `False`,
  rejects *before* calling any provider. Permissive (no error) when no
  structured blocking data exists yet - same "skip, don't fabricate a
  check" precedent as `check_scene_blocking`.
- **API** - `POST /video-productions/{id}/takes/lip-sync` (body:
  `source_video_asset_id`, `source_audio_asset_id`, `duration_seconds`,
  optional `aspect_ratio`/`character_id`). 422 on
  `NoEligibleProviderError`, 409 on `LipSyncEligibilityError`, 404/410 if
  a source asset row/file is missing.
- No migration needed - reuses the existing `ShotVideoProduction`/`Asset`
  machinery entirely.
- Acceptance criterion met: TTS dialogue can become a versioned lip-synced
  clip behind a replaceable provider contract, with full source lineage
  (`source_reference_asset_ids=[video_asset_id, audio_asset_id]`) -
  verified by 4 new service tests (lineage/sources-untouched, capability
  rejection, non-visible-speaker rejection, permissive-without-blocking-
  data) plus an extended end-to-end API test chaining video -> audio ->
  lip-sync generation.

### MODULE-037 / MODULE-038 - Music Engine, Sound Effects

- **`RightsMetadata`** (`domain/rights.py`) - shared by both cue types
  (source, license_type, rights_owner, license_reference); `is_known`
  (non-empty and not `"unknown"` `license_type`) is the single gate both
  services check before approving a cue - "prevent unlicensed/unknown
  provenance assets from publish-ready state" enforced identically for
  music and SFX rather than two divergent implementations.
- **`MusicCue`**/**`SoundEffectCue`** (`domain/music.py`,
  `domain/sound_effect.py`) - planning metadata (purpose/mood/timing/
  ducking for music; description/timing/gain for SFX) plus an `asset_id`
  pointer once one is selected. Cues carry no audio bytes themselves -
  "expose normalized audio to editor" is satisfied structurally by
  pointing at an already-normalized `Asset` (Module 04), no new
  normalization step needed.
- **`MusicCueService`/`SoundEffectCueService`** - `create_cue` (draft) ->
  `link_asset` ("library asset selection first" - a generation provider is
  explicitly optional per the module spec and isn't wired up here) ->
  `approve_cue`, which raises `CueNotReadyError` if no asset is linked or
  `PermissionError` if `rights.is_known` is `False`. Re-linking a
  different asset resets an approved cue back to `draft` - approval never
  silently survives a changed source.
- **`pipeline/sfx_derivation.py:derive_sfx_candidates`** - deterministic
  keyword-based SFX candidate extraction from a shot's micro-beats
  (preferred - real timing) and free-text `action` (fallback - a short
  default window), capped at `MAX_SFX_CANDIDATES_PER_SHOT = 2` per shot -
  "avoid overfilling scenes with unnecessary effects." No LLM call.
  `SoundEffectCueService.derive_candidates_for_shot` persists the results
  as draft cues ready for a human to link an asset to.
- **API** - `POST/GET /episodes/{id}/music-cues`, `GET /music-cues/{id}`,
  `POST /music-cues/{id}/link-asset|/approve`, `DELETE /music-cues/{id}`;
  the same shape for `/sound-effect-cues`, plus
  `POST /episodes/{id}/scenes/{n}/shots/{n}/sound-effect-cues/derive`.
  `approve` returns 409 for `CueNotReadyError`/`PermissionError` (cue
  exists but isn't ready), 404 for a genuinely unknown cue.
- **Migration** - `alembic/versions/55a6461be3fa_add_music_and_sound_effect_cues.py`
  (`music_cues`, `sound_effect_cues`).
- Acceptance criterion met: episodes have auditable music cues ready for
  deterministic mixing, and SFX are structured timeline inputs rather than
  manual post-production notes - verified by 38 new tests (rights/domain,
  SFX-derivation keyword/timing/cap behavior, both repositories, both
  services' approve-gating/re-link-resets-approval, and end-to-end API
  coverage for both cue types).

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

- Real (paid/free) video/voice/lip-sync provider adapters and real
  `ffmpeg` last-frame extraction verification - the contracts/router/
  registries/fake extractor these will plug into already exist.
- Character motion/performance mapping (MODULE-033), voice/dialogue/lip-
  sync/music/SFX/subtitles (MODULE-034-039), job queue/worker/retry
  (MODULE-041-043), multimodal QC/retakes (MODULE-044-045), FFmpeg
  assembly/versioning/export (MODULE-046-048), cost/observability
  (MODULE-049-050), remaining APIs/frontend (MODULE-051-060),
  analytics/learning (MODULE-061-065), security/deployment/hardening
  (MODULE-066-070), testing/eval frameworks (MODULE-071-076),
  backup/migration/docs/release (MODULE-077-080).
- PostgreSQL/S3 adapters (repository/storage interfaces are ready for this;
  no concrete implementation exists yet - ADR-021/ADR-022).
- See `modules/README.md` for the full authoritative MODULE-001..080 queue.
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
