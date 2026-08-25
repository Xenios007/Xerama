# Release Notes & Known Limitations (MODULE-080)

The final release gate for the MODULE-001..080 architecture queue.
`docs/IMPLEMENTATION_STATUS.md` is still the living, per-module source
of truth for what's built; this document is the one-page answer to "is
it release-ready, and what should an operator know before running it
for real."

## Release gate

```bash
python scripts/release_checklist.py            # full check, including frontend
python scripts/release_checklist.py --backend-only
```

Runs, in order: `git status` (informational), `alembic heads` (single-
head check), a migration applied to a scratch DB, a real backup/verify/
restore round-trip (MODULE-077), the full backend test suite, the E2E
production flow alone (MODULE-075), the worker/restart-resume tests
(MODULE-074/076), `pip-audit`, a TODO/FIXME/`NotImplementedError` sweep
across `src/xerama` and `frontend/src`, `scripts/smoke_test.sh`
(clean-environment startup - MODULE-069), and (unless `--backend-only`)
the frontend typecheck/lint/test/build. Prints a PASS/FAIL line per
check and exits non-zero if anything failed.

**Last run (2026-08-25): every check passed - `RELEASE READY`.** 742
backend tests + 2 conditionally-skipped (real FFmpeg/ffprobe, not
installed in this environment - see below), 27 frontend tests, zero
TODO/FIXME/`NotImplementedError` markers found anywhere in `src/xerama`
or `frontend/src`, zero known dependency vulnerabilities.

## Core fake-provider correctness: verified

Every pipeline stage - concept generation, judge/merge, series bible,
characters, season plan, episode outlines/scripts, shot planning, image/
video/voice/lip-sync generation, multimodal QC, automatic retakes,
FFmpeg assembly/versioning/export, subtitles, cost/analytics/eval
tracking, the job queue/worker, authorization, rate limiting - works
end to end against fake/deterministic providers with no paid API key,
proven by `pytest -m e2e` (MODULE-075) and the full test suite. This is
what "release ready" means here: the *architecture* is complete and
exercised, not that every external integration has been verified
against a real vendor.

## Optional live-provider verification: pending

These need a real credential/binary this environment doesn't have, and
were explicitly out of scope to block on (`modules/README.md`'s own
rule: "missing optional credentials are not a blocker"). Each already
has a real contract/router/fake implementation ready for the adapter to
plug into - swapping one in touches no pipeline/service code:

- **OpenRouter LLM calls** - the adapter (`providers/openrouter.py`) is
  real and used by default; only the *free-tier model catalog snapshot*
  it falls back to (`config.py`, dated 2026-08-24) needs periodic
  re-verification against the live catalog, not a code change.
- **Image/video/voice/lip-sync/vision-QC providers** - only fakes exist
  (MODULE-029/032/034/036/044); a real adapter for any of these
  satisfies the same `providers/*.py` Protocol and needs no other
  change (`docs/DEPLOYMENT.md`, `docs/TESTING.md` section 3).
- **Real FFmpeg/ffprobe** - `tests/test_integration.py` has two tests
  gated on `shutil.which("ffmpeg"/"ffprobe")`; both currently skip in
  this environment (the binaries aren't installed here) and will run
  for real wherever they are (MODULE-046/048/074).
- **Hosted PostgreSQL / object storage** - `docs/DEPLOYMENT.md` section
  7 documents the swap (`DATABASE_URL`, a new `StorageProvider`
  implementation); neither adapter exists in code yet - ADR-021/022's
  seam is ready, nothing has exercised it against a real Postgres/S3
  instance.

## Known limitations

- **`get_or_create`-style repository methods have a TOCTOU race** under
  true concurrent first callers (`StyleBibleRepository.get_or_create`
  and likely `get_or_create_storyboard`/`get_or_create_production` -
  same shape). A loud `IntegrityError` (500), not silent corruption, but
  not yet a handled 409/retry. Found during MODULE-068, not fixed
  (unrelated to that module's scope); not yet audited codebase-wide.
- **Worker-lease recovery has no periodic caller** - `JobRepository.recover_abandoned`/
  `JobWorker.reclaim_abandoned` are real and tested (MODULE-041/043/074),
  but nothing invokes them on a schedule, because no out-of-process
  worker exists yet to need it (Trial 01 runs generation synchronously
  in the request - `docs/ARCHITECTURE.md` section 14). Matters only once
  a real background worker process is added; see `docs/DEPLOYMENT.md`
  section 4.
- **`GET /jobs/queued` is not project-scoped** in hosted mode - it's a
  worker-claim/ops introspection view with no project filter in its
  underlying data model, so per-project authorization doesn't apply to
  it (MODULE-067). `GET /jobs`/`GET /jobs/failed` require an explicit
  `project_id` in hosted mode instead of defaulting to an unscoped
  (cross-tenant) listing.
- **`Showrunner.run()` auto-generates only episode 1** end to end, by
  design - episodes 2..N need an explicit follow-up call
  (`POST /series/{id}/episodes/generate-next` or `/generate` - MODULE-002).
- **The in-process `RateLimiter` (MODULE-068) is per-worker**, not
  shared across processes - a genuine multi-process hosted deployment
  should move it to a shared backend (Redis token bucket, etc.) before
  scaling horizontally (`docs/DEPLOYMENT.md` section 4).

See `docs/IMPLEMENTATION_STATUS.md`'s "Partially implemented"/"Planned
(not started)" sections for the complete, continuously-updated list -
the summary above is a snapshot as of this release, not a replacement
for it.

## Versioning

`pyproject.toml`'s `version` and `CHANGELOG.md`'s most recent dated
section are the release identifier - see `CHANGELOG.md` for the full,
per-module change history.
