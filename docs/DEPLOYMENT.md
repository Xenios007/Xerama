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

## 8. Clean-environment smoke test

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
