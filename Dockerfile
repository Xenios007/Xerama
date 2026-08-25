
# Xerama API/worker image (MODULE-069). See docs/DEPLOYMENT.md for the
# full topology (this image serves the API and runs the in-process
# synchronous worker - docs/ARCHITECTURE.md section 14 - not a separate
# process yet). The frontend (frontend/) is a static build served
# independently - it is not baked into this image.

FROM python:3.12-slim

# ffmpeg/ffprobe are optional at the application layer (MODULE-046/048
# fall back to fake providers when the binaries are absent) but required
# for a real, non-fake production run - install them so this image is
# "real" by default rather than silently degraded.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./

RUN pip install --no-cache-dir .

# Persistent volumes in a real deployment - SQLite db file and local
# asset storage (ADR-021/022). Mount these; do not rely on the
# container's writable layer surviving a restart.
VOLUME ["/app/data"]
ENV DATABASE_URL=sqlite+aiosqlite:////app/data/xerama.db
ENV ASSET_STORAGE_PATH=/app/data/storage

EXPOSE 8000

# Applies pending Alembic migrations, then starts the API. See
# docs/DEPLOYMENT.md "Startup sequence" for why migration must run
# before uvicorn binds (schema must be current before serving traffic).
CMD ["sh", "-c", "alembic upgrade head && uvicorn xerama.api.app:app --host 0.0.0.0 --port 8000"]
