# Deployment Architecture (MODULE-069)

"Define reproducible local and hosted deployment without coupling domain
logic to infrastructure." This document is the map; the infrastructure
choices it describes (repository pattern - ADR-021, local storage
provider - ADR-022, `xerama_mode` - MODULE-067, in-memory rate limiting
- MODULE-068) already exist in code for exactly this reason: every
swap named below is a configuration change or a repository/provider
implementation swap, never a change to pipeline/domain code.

## 1. Component topology

```text
                         ┌─────────────────────┐
  Browser  ── HTTP ──►   │  Frontend (static)   │   Vite build served by
                         │  frontend/dist        │   any static host/CDN/
                         └─────────┬─────────────┘   nginx - never Xerama's
                                   │ fetch()               own process.
                                   ▼
                         ┌─────────────────────┐
                         │  API (FastAPI/       │   Also runs the
                         │  uvicorn)             │   synchronous in-process
                         │  xerama.api.app:app   │   worker (Trial 01 -
                         └─────────┬─────────────┘   see section 4).
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                     ▼
     ┌────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
     │ Database         │  │ Asset storage     │  │ ffmpeg / ffprobe      │
     │ SQLite (local) /  │  │ local filesystem / │  │ binaries on PATH -    │
     │ PostgreSQL        │  │ object storage      │  │ MODULE-046/048 fall   │
     │ (hosted, planned) │  │ (hosted, planned)   │  │ back to fake          │
     │ - ADR-021          │  │ - ADR-022            │  │ providers if absent.  │
     └────────────────┘  └──────────────────┘  └──────────────────────┘
```

Every arrow on the right three boxes is a repository/provider Protocol
implementation (`repositories/interfaces.py`, `providers/*.py`) selected
at startup (`api/app.py`'s `lifespan`) - swapping the concrete class is
the entire migration, application code never branches on which one is
active.

## 2. Local Trial-01 (SQLite + local storage) - the only deployment
   verified end-to-end today

```bash
# Backend
python -m venv .venv
.venv/Scripts/activate          # or: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env            # fill in OPENROUTER_API_KEY if you have one -
                                 # every stage still runs with fake providers
                                 # and free-tier models without it
alembic upgrade head
uvicorn xerama.api.app:app --reload

# Frontend (separate terminal)
cd frontend
cp .env.example .env
npm install
npm run dev
```

`GET /health` (liveness, no DB dependency) and `GET /health/ready`
(readiness - actually queries the DB) are available immediately;
`frontend`'s dev server proxies to `VITE_API_BASE_URL`
(`frontend/.env.example`, defaults to `http://localhost:8000`).

## 3. Container path (same topology, reproducible on a clean machine)

```bash
docker compose up --build
```

`Dockerfile` builds a `python:3.12-slim` image with `ffmpeg` installed
(so a container run is "real," not silently degraded to fake
providers), installs the package, and on start runs `alembic upgrade
head` before `uvicorn` binds - schema must be current before the
process accepts traffic (see section 6). `docker-compose.yml` mounts a
named volume at `/app/data` for the SQLite file and asset storage, so
data survives a container restart/rebuild. The frontend is
deliberately **not** built into this image - it's a static bundle
(`npm run build` → `frontend/dist/`) served by whatever static
host/CDN/nginx config the deployment uses; baking a frontend build into
a backend API image would couple two independently-deployable
artifacts for no benefit.

## 4. Process model

Trial 01 runs the "worker" in-process and synchronously within the HTTP
request that triggers generation (docs/ARCHITECTURE.md section 14: "a
simple SQLite-backed local worker is acceptable for Trial 01" -
MODULE-041/042 built the job-queue *data model* - `claim`/`heartbeat`/
`succeed_job`/`fail_job_attempt`/`recover_abandoned` - for a future
out-of-process worker, but no separate worker process consumes it yet).
One API process is both "API" and "worker" today; a future scale-out
would run a separate `xerama.worker` entrypoint against the same
`JobRepository.claim` polling loop the schema already supports, without
changing the job-queue contract.

**Rate limiting/concurrency guards (MODULE-068) are in-process, per
worker.** `RateLimiter` lives in `app.state`, not a shared store -
running more than one API process behind a load balancer means each
process enforces its own independent limits (effectively multiplying
the configured ceiling by the process count). Fine for Trial 01's
single-process deployment; a genuine multi-process hosted deployment
should move this to a shared backend (Redis token bucket, etc.) behind
the same `RateLimiter` interface before scaling out - not yet built,
documented here as the scaling boundary.

## 5. Environment separation

- **`XERAMA_MODE`** (`standard` default / `hosted`) - MODULE-067's
  authorization gate. `standard`: no user/session/membership check
  anywhere, single trusted operator, matches every local/Trial-01 run.
  `hosted`: every project-scoped endpoint requires a Bearer session
  token and a `ProjectMembership` role - see `docs/IMPLEMENTATION_STATUS.md`
  MODULE-067 for exactly what's covered.
- **`CORS_ALLOWED_ORIGINS`** - comma-separated; never `*` once
  `XERAMA_MODE=hosted` issues credentialed bearer tokens to browsers.
- **Secrets** - `OPENROUTER_API_KEY` is a Pydantic `SecretStr` (never
  logged/repr'd - MODULE-002/066); pass it via the container/orchestrator's
  secret mechanism in a hosted deployment, never bake it into an image
  layer or commit it (`.env` is gitignored).
- **Rate/budget ceilings** (`RATE_LIMIT_*`, `PROJECT_BUDGET_CEILING_USD`
  - MODULE-068) - permissive by default; a hosted deployment should set
  these explicitly per section 4's scaling caveat.

## 6. Startup sequence

1. Apply migrations (`alembic upgrade head`) - **before** the API binds,
   not lazily on first request; a partially-migrated schema serving
   traffic is a strictly worse failure mode than a slow/failed startup.
2. `create_all(engine)` in `lifespan()` is a no-op once migrations have
   run (SQLAlchemy's `create_all` skips existing tables) - kept as a
   defense-in-depth safety net for a fresh SQLite file, not a substitute
   for step 1.
3. Health checks: `GET /health` (liveness - process is up, no
   dependencies) should gate container/orchestrator restart decisions;
   `GET /health/ready` (readiness - `SELECT 1` against the DB) should
   gate traffic admission (load balancer / ingress).

## 7. Hosted path (PostgreSQL + object storage) - documented, not yet
   implemented

docs/ARCHITECTURE.md section 14 explicitly defers this past Trial 01
("PostgreSQL/S3 deployment ... can wait until the pilot works"). The
seam already exists and is exercised by the interface/implementation
split every module in this codebase already follows:

- **Database**: `DATABASE_URL` is read by `db/base.py::make_engine` via
  SQLAlchemy's async engine factory - pointing it at a
  `postgresql+asyncpg://...` DSN is the entire schema-level change
  (ADR-021); every repository is written against `repositories/interfaces.py`
  Protocols, never raw SQL, so no repository code should need to change.
  Alembic migrations are already dialect-agnostic standard `sa.*`
  operations (no SQLite-specific DDL) - the same migration chain should
  apply directly.
- **Asset storage**: `providers/storage.py`'s `StorageProvider` Protocol
  is implemented today only by `LocalStorageProvider` (ADR-022). A
  hosted deployment needs an S3/GCS-backed implementation of the same
  three methods (`save_bytes`/`read_bytes`/`delete`, plus `exists`/
  `list_all`) wired into `app.py`'s `lifespan` in place of
  `LocalStorageProvider` - no service/router code depends on which one
  is active, they only ever go through `AssetService`.
- **Not yet built**: neither adapter exists in code. This section is
  the roadmap for MODULE-069's own "document ... the hosted path"
  requirement, not a claim that hosted persistence works today.

### 7.1 Data export/import (MODULE-078)

Migrating an existing local Trial-01 project into a hosted deployment
is two independent transfers - the schema-level swap above only
prepares the *target* to accept data, it doesn't move any:

- **Database**: `pg_dump`/`pg_restore` (or an ETL tool of choice) against
  the *same schema* the Alembic chain already produces - run
  `alembic upgrade head` against the empty target Postgres DB first
  (creates every table with the right types/indexes), then copy row
  data table-by-table. Every ID in this schema is already an
  application-generated UUID hex string (`db/models.py::_id()`), never a
  DB-native auto-increment integer - so row identity is stable across
  the copy with no ID-remapping step, and foreign-key-shaped columns
  (`project_id`, `episode_id`, etc. - see `repositories/sqlalchemy_impl.py`
  for which are real FKs vs. plain indexed strings) never need
  rewriting either.
- **Asset storage / "asset-key mapping"**: `Asset.storage_path` (e.g.
  `"a1/a1b2c3....png"`, content-hash-prefixed - ADR-020/022) is already
  the *object key* an S3/GCS adapter would use verbatim - `storage_path`
  was deliberately designed as a flat relative path, never a local
  filesystem assumption (no drive letters, no `..`, enforced by
  `LocalStorageProvider._safe_path`), so migrating assets is "upload
  every file under `ASSET_STORAGE_PATH` to the bucket using its existing
  relative path as the object key" with **no key-mapping table needed**
  - the DB rows' `storage_path` values stay valid unmodified once the
  bucket is populated. `python -m xerama.backup`'s manifest.json
  (MODULE-077) already enumerates every relative path + hash, so it
  doubles as the file list to upload; verify post-upload by comparing
  each object's hash against that same manifest.
- **Order**: restore/import the database first, then upload assets - a
  DB row referencing a `storage_path` that isn't in the bucket yet is a
  visible, debuggable 404 on asset download; an asset in the bucket with
  no DB row is invisible and harmless. Never the other order.

## 8. Operational limits & hardening (MODULE-070)

"Remove prototype-only failure modes before calling the system
production-ready" - what this covers, and what's still a documented
boundary rather than a fix:

- **FFmpeg/ffprobe subprocess timeout** - a malformed/pathological input
  can otherwise hang `ffmpeg`/`ffprobe` indefinitely, and since
  generation runs synchronously within the HTTP request (section 4),
  that would hang the request forever too. Every real subprocess call
  (`providers/ffmpeg_assembler.py`, `ffmpeg_frame_extractor.py`,
  `ffprobe_inspector.py`) now goes through
  `providers/subprocess_utils.py::communicate_with_timeout`, which kills
  the process and fails cleanly past `FFMPEG_TIMEOUT_SECONDS` (default
  300s) instead. `FFmpegAssembler`/`FFmpegFrameExtractor` raise their
  existing error types; `FFprobeInspector` returns its existing
  `MediaProbeResult(ok=False, ...)` soft-failure shape - both match each
  provider's pre-existing failure contract, nothing new for callers to
  handle.
- **Unhandled exceptions** - never leak internals (a generic
  `{"detail": "internal server error"}` 500 regardless of what actually
  broke) and are always logged with structured, correlation-ID-tagged
  context (`api/middleware.py`'s `correlation_id_middleware` - see that
  module's docstring for why this lives in the middleware rather than a
  `@app.exception_handler(Exception)` registration, which silently
  doesn't fire with this middleware stack).
- **DB connections** - `pool_pre_ping=True` (`db/base.py::make_engine`)
  replaces a stale/dead pooled connection transparently instead of
  failing the next real query with a cryptic error. Matters most for a
  hosted PostgreSQL deployment (section 7); a no-op cost for SQLite's
  single local connection.
- **Upload size / rate / concurrency / budget limits** - MODULE-066/068,
  see sections 5 above and their own `docs/IMPLEMENTATION_STATUS.md`
  entries.
- **Debug-only shortcuts** - none found in an explicit audit
  (`debug=True`, a hardcoded `allow_origins=["*"]`, `reload=True`, or a
  TODO/FIXME/HACK marker in `src/xerama`) - `FastAPI()` never sets
  `debug=True`, so no traceback ever reaches a client regardless of the
  handler above.
- **Documented boundary, not fixed here**: worker leases
  (`JobRepository.claim`/`heartbeat`/`recover_abandoned` - MODULE-041/043)
  are real and tested, but nothing calls `recover_abandoned()`
  periodically today, because no out-of-process worker consumes the
  lease-based queue path yet (section 4) - it would only matter once
  that worker exists. A future worker process must call it on startup
  and periodically, or an abandoned `running` job (its worker crashed
  mid-lease) would stay `running` forever.
- **Documented boundary, not fixed here**: a small number of
  `get_or_create`-style repository methods have a TOCTOU race under true
  concurrent first callers (found while testing MODULE-068 - see that
  module's entry in `docs/IMPLEMENTATION_STATUS.md`) - a loud
  `IntegrityError` (500), not silent corruption, but not yet a handled
  409/retry.

## 9. Backup and recovery (MODULE-077)

`python -m xerama.backup {backup|verify|restore}` - protects the SQLite
DB and local asset store (Trial 01's persistence path - ADR-021/022)
from local failure or operator error.

```bash
python -m xerama.backup backup --backup-dir ./backups
# -> Backup created at ./backups/xerama-backup-<UTC timestamp>/

python -m xerama.backup verify ./backups/xerama-backup-<timestamp>
# -> Backup integrity check passed - every file matches its manifest hash.

python -m xerama.backup restore ./backups/xerama-backup-<timestamp>
```

- **Consistency**: the DB copy uses SQLite's own backup API
  (`sqlite3.Connection.backup`), not a raw file copy - safe even if the
  API process has the DB open concurrently; a plain `cp` on a live
  SQLite file can capture a torn/mid-write page.
- **Integrity**: every backed-up file (the DB snapshot and every asset)
  is SHA-256-hashed into a `manifest.json`; `verify`/`restore` recompute
  and compare every hash - `restore` refuses to touch anything if even
  one file fails verification, rather than partially restoring from a
  corrupt backup.
- **Version lineage and configuration**: both already live inside the
  one SQLite file this backs up - every `EpisodeRender` version (never
  overwritten - ADR-019/047) and the applied Alembic migration
  (`alembic_version` table) - so a full-file backup preserves both
  automatically, no separate export step needed.
- **Scope**: local SQLite + filesystem storage only - `backup.py`
  raises immediately (rather than silently doing the wrong thing) if
  `DATABASE_URL` isn't a `sqlite+aiosqlite:///` URL.

**Hosted path** (documented, not implemented here - matches section 7's
"documented, not yet implemented" PostgreSQL/object-storage path): a
hosted PostgreSQL deployment should use `pg_dump`/`pg_basebackup` (or
the managed provider's native point-in-time-recovery/snapshot feature)
instead of this script; a hosted object-storage asset store should rely
on that store's own versioning/cross-region replication (S3 versioning,
GCS object versioning, etc.) rather than a filesystem `copytree`. Both
are standard, well-understood backup mechanisms for their respective
systems - reinventing them here would only add risk.

## 10. Clean-environment smoke test

`scripts/smoke_test.sh` proves "a new machine can start Xerama from
documented steps with no hidden local assumptions" (this module's own
"Done when" line) by actually doing it: fresh venv, `pip install -e .`
(no dev extras - the real install path), migrations against a scratch
DB, a real `uvicorn` process boot, then polling `/health` and
`/health/ready` until both succeed (or a timeout fails the script).
Run it from a clean checkout:

```bash
bash scripts/smoke_test.sh
```
