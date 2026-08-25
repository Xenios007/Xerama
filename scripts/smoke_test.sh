#!/usr/bin/env bash
# MODULE-069 - clean-environment startup smoke test. Proves "a new
# machine can start Xerama from documented steps with no hidden local
# assumptions" (this module's own "Done when" line) by actually doing
# every step docs/DEPLOYMENT.md describes: fresh venv, a real (non-dev)
# `pip install`, migrations against a scratch DB, a real `uvicorn`
# process boot, then polling health/readiness until both succeed.
#
# Run from the repo root: bash scripts/smoke_test.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

WORK_DIR="$(mktemp -d)"
# On Git Bash/MSYS, a POSIX path like /tmp/xyz is only auto-translated
# to a real Windows path when it's a whole argv entry - not when it's
# embedded inside a larger string like a DATABASE_URL DSN. Compute a
# Windows-safe form (forward slashes, drive letter) for anything that
# gets embedded in such a string; keep using $WORK_DIR as-is for plain
# bash file operations (mktemp/cat/rm).
if command -v cygpath >/dev/null 2>&1; then
    WORK_DIR_URL="$(cygpath -m "$WORK_DIR")"
else
    WORK_DIR_URL="$WORK_DIR"
fi
VENV_DIR="$WORK_DIR/venv"
DB_PATH="$WORK_DIR_URL/smoke.db"
STORAGE_PATH="$WORK_DIR_URL/storage"
PORT=8321
SERVER_PID=""

cleanup() {
    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

echo "== [1/5] Creating a fresh virtualenv (no dev extras) =="
python -m venv "$VENV_DIR"
if [ -f "$VENV_DIR/Scripts/python.exe" ]; then
    PY="$VENV_DIR/Scripts/python.exe"  # Windows venv layout
else
    PY="$VENV_DIR/bin/python"          # POSIX venv layout
fi

echo "== [2/5] pip install -e . (the real install path, not [dev]) =="
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -e .

echo "== [3/5] Applying migrations to a scratch database =="
export DATABASE_URL="sqlite+aiosqlite:///$DB_PATH"
export ASSET_STORAGE_PATH="$STORAGE_PATH"
"$PY" -m alembic upgrade head

echo "== [4/5] Starting uvicorn =="
"$PY" -m uvicorn xerama.api.app:app --host 127.0.0.1 --port "$PORT" \
    > "$WORK_DIR/server.log" 2>&1 &
SERVER_PID=$!

echo "== [5/5] Polling /health and /health/ready =="
READY=0
for _ in $(seq 1 30); do
    if curl -sf "http://127.0.0.1:$PORT/health" > /dev/null 2>&1 \
        && curl -sf "http://127.0.0.1:$PORT/health/ready" > /dev/null 2>&1; then
        READY=1
        break
    fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        echo "uvicorn exited early - server log:"
        cat "$WORK_DIR/server.log"
        exit 1
    fi
    sleep 1
done

if [ "$READY" -ne 1 ]; then
    echo "timed out waiting for /health and /health/ready - server log:"
    cat "$WORK_DIR/server.log"
    exit 1
fi

echo "OK: clean-environment install, migration, and startup all succeeded."
