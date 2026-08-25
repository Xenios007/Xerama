# Testing Architecture (MODULE-071)

"Contributors/agents can verify changes reproducibly without paid APIs."
This document is the map of how ~94 backend test files (668 tests + 2
conditionally-skipped) and 7 frontend test files (27 tests) are
organized, what each layer covers, and how to run all of it from a
clean checkout.

## 1. Running everything

```bash
# Backend
pip install -e ".[dev]"
pytest -q                              # every test, unit + integration
pytest -m "not integration" -q         # fast unit-only subset
pytest -m integration -q               # MODULE-074 - cross-subsystem tests only
pytest --cov=xerama --cov-report=term-missing   # coverage (pytest-cov, MODULE-071)

# Frontend
cd frontend
npm install
npm test -- --run                      # 27 tests, ~15s
npm run typecheck
npm run lint
npm run build
```

No step above requires `OPENROUTER_API_KEY` or any other paid credential
- every provider boundary is faked (section 3).

## 2. Unit / integration / E2E boundaries

Three layers, from fastest/most-isolated to slowest/most-realistic. A
change should be tested at the *lowest* layer that can actually catch a
regression in it - a pure function bug belongs in a layer-1 test, not
rediscovered by an E2E test three layers up.

1. **Pure unit tests** - no DB, no HTTP, no fixtures beyond plain
   Python objects. Everything in `pipeline/*.py` is written to be
   testable this way (deterministic functions/validators/builders take
   domain objects in, return domain objects out - e.g.
   `pipeline/rate_limiting.py`, `pipeline/cost_aggregation.py`,
   `pipeline/story_performance.py`). Fastest category by a wide margin
   (`tests/test_rate_limiting.py`'s 12 tests run in 0.07s) - prefer this
   layer whenever the logic under test doesn't inherently need
   persistence.
2. **Repository/service integration tests** - real SQLAlchemy against a
   real (temporary, file-backed) SQLite database via the `session`
   fixture (`tests/conftest.py`). Proves the actual SQL, not a mocked
   ORM - `tests/test_*_repository.py` and `tests/test_*_service.py`
   files. A real temp *file* (not `:memory:`) is used deliberately -
   `:memory:` databases are per-connection in SQLite, and aiosqlite's
   connection pooling would otherwise make different queries in the
   same test silently see different, disconnected databases.
3. **API/E2E tests** - a real `httpx.AsyncClient` driving the actual
   FastAPI app (`httpx.ASGITransport` - no real network socket, but the
   full ASGI stack: middleware, dependency injection, routing) against
   a temporary DB/storage directory. `tests/test_api.py` is the primary
   file (the `client` fixture); `tests/test_api_hosted_mode.py`,
   `tests/test_api_rate_limiting.py`, and `tests/test_large_project.py`
   each define their own narrower `client` fixture rather than reusing
   `test_api.py`'s, because each needs different `app.state` wiring
   (hosted-mode auth, a deliberately tight `RateLimiter`, a leaner
   provider set) that would otherwise complicate the shared fixture with
   parameters only one test file needs.

Frontend mirrors this: component tests (`frontend/src/**/*.test.tsx`,
Vitest + Testing Library) mock only the `fetch` boundary
(`frontend/src/api/client.ts`), exercising real React Query/Router
behavior around it - the frontend's equivalent of layer 3.

## 3. Fake providers - why CI never needs a paid API

Every external integration in this codebase follows "contract + fake
now, real adapter later" (the pattern behind nearly every MODULE in
006-048): a Protocol in `providers/*.py`, a real (or not-yet-built)
adapter, and a `Fake*` implementation used everywhere in tests and in
the default app wiring when no real credential/binary is configured.

| Boundary | Protocol | Fake used in tests |
|---|---|---|
| LLM completion | `providers/llm.py::LLMProvider` | `FakeLLMProvider` (scripted response queue) |
| Image generation | `providers/image.py::ImageProvider` | `FakeImageProvider` |
| Video generation | `providers/video.py::VideoProvider` | `FakeVideoProvider` |
| Voice generation | `providers/voice.py::VoiceProvider` | `FakeVoiceProvider` |
| Lip sync | `providers/lip_sync.py::LipSyncProvider` | `FakeLipSyncProvider` |
| Vision-based QC | `providers/media_qc.py::MediaQCProvider` | `FakeMediaQCProvider` |
| Last-frame extraction | `providers/frame_extractor.py::FrameExtractor` | `FakeFrameExtractor` |
| Episode assembly (FFmpeg) | `providers/assembler.py::EpisodeAssembler` | `FakeAssembler` |
| Export validation (ffprobe) | `providers/media_inspector.py::MediaInspector` | `FakeMediaInspector` |

`test_api.py`'s `client` fixture wires every one of these to its fake
by default and exposes each on the client (`client.fake_image_provider`,
etc.) so a test can `.queue(...)` a specific response or flip a
capability flag. The three real subprocess-backed providers
(`FFmpegAssembler`/`FFmpegFrameExtractor`/`FFprobeInspector`) are
exercised only by `scripts/smoke_test.sh` and manual runs where the
binaries are actually installed - `app.py`'s `lifespan` already falls
back to the fakes automatically when `ffmpeg`/`ffprobe` aren't on
`PATH`, so this is the correct behavior in CI, not a coverage gap to
close.

## 4. Isolation

- **DB**: every fixture that needs one creates a fresh SQLite file under
  pytest's `tmp_path` and disposes the engine on teardown - no test
  shares state with another, and nothing is left on disk after a run.
- **Storage**: `LocalStorageProvider` is always pointed at a `tmp_path`
  subdirectory, same reasoning.
- **Settings**: `config.get_settings()` is `@lru_cache`d process-wide: a
  test that needs a different env var (upload size ceiling, rate
  limits, `XERAMA_MODE`, budget ceiling) must call
  `get_settings.cache_clear()` after `monkeypatch.setenv(...)` and again
  in a `finally`/fixture-teardown to avoid leaking the override into the
  next test. Search `get_settings.cache_clear` across `tests/` for the
  established pattern.
- **In-memory singletons**: `RateLimiter` (MODULE-068) and
  `ProviderHealthTracker` (ADR-011) are process-lifetime state on
  `app.state` in real deployments; every test fixture that builds its
  own `app` constructs a fresh instance of each, so no test's rate-limit
  window or provider-health circuit leaks into another test.

## 5. Coverage

`pytest --cov=xerama --cov-report=term-missing` (2026-08-25 baseline):
**87% overall**, and effectively 100% across `domain/`, most of
`pipeline/`, and `repositories/interfaces.py`. This is not a coverage
*gate* (no CI exists to enforce one - MODULE-069/070) but a baseline for
judging where a real gap is versus where a shortfall is expected and
fine:

- **Router files sit lower (35-65%)** - largely the multi-branch
  `HTTPException` paths for every distinct failure mode (404/409/422/
  etc.) across many endpoints; the *service/pipeline* logic each router
  calls into is what's actually at or near 100%. A missing router
  branch here is lower-value to chase than a missing branch in
  `pipeline/` or `services/`, which is where the real logic lives.
- **The three real FFmpeg/ffprobe subprocess providers are near 0%** -
  by design (section 3) - not exercised unless the binaries are
  installed.
- Two real gaps this module found and closed: `cli.py` (0% - a second,
  independently-wired entrypoint that reused the exact same
  Showrunner/AIGateway/repository construction as the API but had never
  been run under test - `tests/test_cli.py` now exercises it end-to-end
  with a faked LLM provider) and `providers/identity_qc.py` (0% -
  confirmed-dead code: its own docstring said it was superseded by
  MODULE-044's `MediaQCProvider`, and nothing imported it - deleted
  rather than tested, since a coverage report is not a reason to keep
  dead code alive).

## 6. Integration tests (MODULE-074)

`tests/test_integration.py` (`@pytest.mark.integration`, registered in
`pyproject.toml`) verifies boundaries *between* subsystems specifically -
every test opens a **fresh** session/connection to read back what an
earlier session wrote, proving the data actually round-tripped through
the DB rather than just still being held as an in-memory Python object
by the writing test (a subtlety layer-2/3 tests elsewhere in the suite
don't need to prove explicitly, since they aren't making a boundary
claim):

- **Story pipeline through persistence** - a full `Showrunner.run()`
  (concept -> judge -> bible -> cast -> season plan -> outlines ->
  episode 1 script/shot plan), then a brand-new session reads the series/
  episodes/bible back.
- **Queued fake media generation through the asset/QC lifecycle** -
  ingest -> QC check -> accept, then a fresh session confirms both the
  `Asset.status` transition and the `MediaQCAttempt` row persisted.
- **API-worker restart/resume** - the scenario a plain repository-level
  `recover_abandoned` test can't fully prove: "worker A" claims a job and
  crashes (lease immediately expired, simulating time passing after a
  real crash) using its own session; a completely separate "worker B"
  instance (its own session and `JobWorker`, matching how a restarted
  process reconnects) reclaims the abandoned lease and processes the job
  to completion; a third, fresh session confirms the final `SUCCEEDED`
  status and result.
- **Real FFmpeg/ffprobe, conditionally** - `@pytest.mark.skipif` on
  `shutil.which("ffmpeg")`/`"ffprobe"`, so this is a no-op (not a
  failure) in the common case where the binaries aren't installed, and
  actually exercises `FFmpegFrameExtractor`/`FFprobeInspector` for real
  on a machine that has them - synthesizing the test clip via ffmpeg's
  own `lavfi` test-source generator, so no external sample-video fixture
  is needed either way.

## 7. Critical state transitions and failure paths - already covered

Spot-checked rather than re-derived (this module is `AUDIT/EXTEND`, not
`BUILD` - the coverage below already existed from each owning module):

- **Asset lifecycle** (`pending -> accepted/rejected`, content-hash
  dedup, versioned-never-deleted rejects - ADR-019/020) -
  `test_asset_service.py`, `test_api.py`.
- **QC gate** (pass/warn/block + reasons + repair recommendation,
  ADR-018) - `test_media_qc.py`.
- **Job queue** (`queued -> running -> succeeded/failed/retrying`,
  lease claim/heartbeat/recover-abandoned, FIFO tie-break) -
  `test_job_queue_repository.py`, `test_job_worker.py`.
- **Provider fallback/health** (capability filter -> health filter ->
  attempt -> fallback on failure) - `test_media_router.py`.
- **Authorization** (401/403/404 boundaries, role ranking, hosted-mode
  no-op contract) - `test_api_hosted_mode.py`.
- **Rate/concurrency/budget guards** (429/402/409, window reset,
  released-on-exit) - `test_rate_limiting.py`, `test_budget_service.py`,
  `test_api_rate_limiting.py`.
- **Migration chain** - `alembic heads` (single head) +
  `alembic upgrade head` against a scratch DB is run manually after
  every new migration (see any MODULE's write-up in
  `docs/IMPLEMENTATION_STATUS.md` for the exact commands); not
  automated into `pytest` since it mutates a real (if scratch) database
  file rather than using the in-memory-per-test pattern the rest of the
  suite follows.
