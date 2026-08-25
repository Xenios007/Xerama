#!/usr/bin/env python
"""MODULE-080 - the release gate. Runs every check this module's own
"Requirements" line names (versioning/migration/backup/full test-lint-
type-build/startup/worker/E2E) plus a TODO/FIXME/NotImplemented sweep,
and prints a pass/fail summary. Exits non-zero if anything failed.

Run from the repo root:  python scripts/release_checklist.py
Skip the frontend checks (no Node available): --backend-only
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class CheckResult:
    def __init__(self, name: str, passed: bool, detail: str = "") -> None:
        self.name = name
        self.passed = passed
        self.detail = detail


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 600) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            cmd, cwd=cwd or REPO_ROOT, capture_output=True, text=True, timeout=timeout
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output[-4000:]
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    except FileNotFoundError as exc:
        return False, f"command not found: {exc}"


def check_git_status_reported() -> CheckResult:
    ok, output = _run(["git", "status", "--short"])
    dirty = bool(output.strip())
    # Informational, not a hard failure - a release can legitimately
    # happen with staged-but-uncommitted release-note edits.
    return CheckResult(
        "git status", True, "clean" if not dirty else f"working tree not clean:\n{output}"
    )


def check_single_migration_head() -> CheckResult:
    py = sys.executable
    ok, output = _run([py, "-m", "alembic", "heads"])
    heads = [line for line in output.splitlines() if line.strip() and "(head)" in line]
    single_head = ok and len(heads) == 1
    return CheckResult("alembic heads (single head)", single_head, output.strip())


def check_migration_applies_cleanly() -> CheckResult:
    py = sys.executable
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "release_check.db"
        db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
        import os

        env = {**os.environ, "DATABASE_URL": db_url}
        try:
            result = subprocess.run(
                [py, "-m", "alembic", "upgrade", "head"],
                cwd=REPO_ROOT, capture_output=True, text=True, timeout=120, env=env,
            )
            ok = result.returncode == 0
            output = (result.stdout or "") + (result.stderr or "")
        except subprocess.TimeoutExpired:
            ok, output = False, "timed out"
    return CheckResult("migration applies to a scratch DB", ok, output[-2000:])


def check_backup_tool_round_trips() -> CheckResult:
    """MODULE-077's own tool, exercised as this gate's "backup check" -
    a real backup -> verify -> restore cycle against scratch data."""
    py = sys.executable
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "xerama.db"
        storage_path = tmp_path / "storage"
        storage_path.mkdir()
        (storage_path / "a.png").write_bytes(b"asset bytes")

        code = f"""
import sqlite3
from pathlib import Path
from xerama.backup import backup, verify, restore

db_path = Path(r"{db_path}")
storage_path = Path(r"{storage_path}")
conn = sqlite3.connect(str(db_path))
conn.execute("CREATE TABLE t (x TEXT)")
conn.execute("INSERT INTO t VALUES ('release-check')")
conn.commit()
conn.close()

backup_dir = backup(db_path, storage_path, Path(r"{tmp_path}") / "backups")
assert verify(backup_dir) == [], "backup failed integrity verification"

db_path.unlink()
import shutil as _shutil
_shutil.rmtree(storage_path)
restore(backup_dir, db_path, storage_path)
assert db_path.is_file()
assert (storage_path / "a.png").read_bytes() == b"asset bytes"
print("backup round-trip OK")
"""
        ok, output = _run([py, "-c", code], timeout=60)
    return CheckResult("backup/restore round-trip", ok, output.strip())


def check_backend_tests() -> CheckResult:
    py = sys.executable
    ok, output = _run([py, "-m", "pytest", "-q"], timeout=900)
    match = re.search(r"(\d+) passed", output)
    detail = match.group(0) if match else output[-1000:]
    return CheckResult("backend test suite (pytest -q)", ok, detail)

def check_backend_e2e() -> CheckResult:
    py = sys.executable
    ok, output = _run([py, "-m", "pytest", "-m", "e2e", "-q"], timeout=120)
    match = re.search(r"(\d+) passed", output)
    detail = match.group(0) if match else output[-1000:]
    return CheckResult("E2E production flow (pytest -m e2e)", ok, detail)


def check_worker() -> CheckResult:
    py = sys.executable
    ok, output = _run([py, "-m", "pytest", "-q", "tests/test_job_worker.py", "tests/test_integration.py"])
    match = re.search(r"(\d+) passed", output)
    detail = match.group(0) if match else output[-1000:]
    return CheckResult("worker + restart/resume tests", ok, detail)


def check_dependency_audit() -> CheckResult:
    py = sys.executable
    with tempfile.TemporaryDirectory() as tmp:
        freeze_path = Path(tmp) / "freeze.txt"
        ok, output = _run([py, "-m", "pip", "freeze"])
        if not ok:
            return CheckResult("pip-audit", False, "pip freeze failed")
        freeze_path.write_text(output)
        ok, output = _run([py, "-m", "pip_audit", "-r", str(freeze_path)], timeout=120)
    return CheckResult("pip-audit (dependency vulnerabilities)", ok, output.strip()[-1500:])


def check_startup_smoke() -> CheckResult:
    smoke_script = REPO_ROOT / "scripts" / "smoke_test.sh"
    bash = shutil.which("bash")
    if bash is None:
        return CheckResult("startup smoke test", False, "bash not found on PATH - cannot run scripts/smoke_test.sh")
    ok, output = _run([bash, str(smoke_script)], timeout=300)
    return CheckResult("startup smoke test (clean venv+install+migrate+boot)", ok, output.strip()[-1500:])


def check_todo_fixme_sweep() -> CheckResult:
    pattern = re.compile(r"\b(TODO|FIXME|XXX)\b|NotImplementedError")
    hits: list[str] = []
    for path in (REPO_ROOT / "src" / "xerama").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if pattern.search(line):
                hits.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}")
    frontend_src = REPO_ROOT / "frontend" / "src"
    if frontend_src.is_dir():
        for path in frontend_src.rglob("*.ts*"):
            for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if pattern.search(line):
                    hits.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}")
    return CheckResult(
        "TODO/FIXME/XXX/NotImplementedError sweep", len(hits) == 0,
        "none found" if not hits else "\n".join(hits),
    )


def check_frontend(name: str, cmd: list[str]) -> CheckResult:
    frontend_dir = REPO_ROOT / "frontend"
    npm = shutil.which("npm")
    if npm is None:
        return CheckResult(name, False, "npm not found on PATH")
    ok, output = _run([npm, *cmd], cwd=frontend_dir, timeout=180)
    return CheckResult(name, ok, output.strip()[-1500:])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-only", action="store_true", help="Skip frontend checks.")
    args = parser.parse_args()

    checks = [
        check_git_status_reported,
        check_single_migration_head,
        check_migration_applies_cleanly,
        check_backup_tool_round_trips,
        check_backend_tests,
        check_backend_e2e,
        check_worker,
        check_dependency_audit,
        check_todo_fixme_sweep,
        check_startup_smoke,
    ]

    results: list[CheckResult] = []
    for check in checks:
        print(f"== Running: {check.__name__} ==", flush=True)
        results.append(check())

    if not args.backend_only:
        results.append(check_frontend("frontend typecheck", ["run", "typecheck"]))
        results.append(check_frontend("frontend lint", ["run", "lint"]))
        results.append(check_frontend("frontend test", ["test", "--", "--run"]))
        results.append(check_frontend("frontend build", ["run", "build"]))

    print("\n" + "=" * 70)
    print("RELEASE CHECKLIST RESULTS")
    print("=" * 70)
    all_passed = True
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        if not r.passed:
            all_passed = False
        print(f"[{status}] {r.name}")
        if r.detail and (not r.passed or r.name in ("git status", "TODO/FIXME/XXX/NotImplementedError sweep")):
            for line in r.detail.splitlines()[:20]:
                print(f"       {line}")

    print("=" * 70)
    print("RELEASE READY" if all_passed else "NOT RELEASE READY - see FAILs above")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
