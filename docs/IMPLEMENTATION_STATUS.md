# Xerama Implementation Status

_Last updated: 2026-08-24 - first coding session (XER-001)._

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
- **Tests** - 39 tests covering schema validation, repository round-trips,
  OpenRouter response parsing + error mapping (respx-mocked, no network),
  AI-gateway repair/retry, judge/merge logic, validator heuristics, full
  pipeline success + mid-pipeline-failure paths, and the HTTP API end to end
  - all against `FakeLLMProvider`, no paid API calls required.

## Partially implemented

- **Character/Style identity** - the textual/structural layer (`Character`,
  `CharacterDNA` fields, `visual_identity_id`/`voice_identity_id` slots)
  exists per ADR-012, but no image generation runs yet, so DNA fields are
  currently populated by the LLM as text only, and identity/voice asset IDs
  stay `null`. Style Bible has no dedicated table yet (deferred - no
  downstream consumer until image generation exists).
- **Provider health** - `ProviderHealthTracker` exists and is used by the AI
  gateway, but there is only one provider (OpenRouter) so there is no
  fallback *across* providers yet, only a circuit-break signal.
- **Jobs** - modeled with the required states and used for every pipeline
  stage, but execution is synchronous within the HTTP request (per
  docs/ARCHITECTURE.md section 14, this is explicitly acceptable for Trial
  01: "a simple SQLite-backed local worker is acceptable"). No background
  worker/queue process exists yet.

## Planned (not started)

- Director/Media Engine: image/video/voice/lip-sync provider adapters,
  Style Bible table, storage provider abstraction, FFmpeg assembly.
- Season/reveal architecture beyond per-episode outlines (XER-006 scope).
- Episode 2+ scripts (outlines exist for the full requested count; only
  Episode 1 gets a full script/shot plan per the XER-001 milestone scope).
- Analytics/learning feedback loop (Phase 5).
- PostgreSQL/S3 adapters (repository/storage interfaces are ready for this;
  no concrete implementation exists yet - ADR-021/ADR-022).

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
4. **Model-role -> stage mapping** - the roadmap/AI_MODELS.md role table
   doesn't say which role owns "series bible", "characters", or "episode
   outlines" specifically. This implementation assigns all three to
   `story_architect` (series/season structure, per its stated
   responsibility), reserves `episode_writer` for episode script prose only,
   and reuses `story_architect` for MERGE-decision concept synthesis (no
   dedicated "concept merger" role exists in the docs).
