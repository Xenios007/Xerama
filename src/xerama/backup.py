"""Local backup/restore for the SQLite DB + local asset store (MODULE-077).

`python -m xerama.backup backup|restore|verify` - see docs/DEPLOYMENT.md
"Backup and recovery" for the full runbook. Scope: Trial 01's local
SQLite + filesystem storage path (ADR-021/022). A hosted PostgreSQL/
object-storage deployment should use that backend's own native backup
tooling (pg_dump/pg_basebackup, S3 versioning/replication) instead of
this script - see that section for why.

The DB copy uses SQLite's own backup API (`sqlite3.Connection.backup`),
not a raw file copy - a plain `cp`/`shutil.copy` on a SQLite file that's
open elsewhere can capture a torn/mid-write page; the backup API is
SQLite's documented mechanism for a *consistent* snapshot regardless of
concurrent access. Version lineage (every `EpisodeRender` version - ADR
"never overwrite/delete a rejected/superseded artifact") and
configuration metadata (the applied Alembic migration - `alembic_version`
table) both live inside the same SQLite file, so a full-file backup
preserves both automatically; no separate export step is needed for
either.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_FILENAME = "manifest.json"
DB_BACKUP_FILENAME = "xerama.db"
STORAGE_BACKUP_DIRNAME = "storage"


class BackupIntegrityError(RuntimeError):
    """Raised by `verify`/`restore` when a backed-up file's hash no
    longer matches its manifest entry - the backup is corrupt and must
    not be restored from."""


@dataclass
class BackupManifest:
    created_at: str
    source_db_path: str
    source_storage_path: str
    files: dict[str, str]  # relative path -> sha256 hex digest


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _backup_sqlite_db(source_db_path: Path, dest_db_path: Path) -> None:
    """A consistent snapshot via SQLite's own backup API - safe even if
    `source_db_path` has an open connection elsewhere (the API handles
    the live-page-copy locking correctly; a raw file copy would not)."""
    source_conn = sqlite3.connect(str(source_db_path))
    dest_conn = sqlite3.connect(str(dest_db_path))
    try:
        source_conn.backup(dest_conn)
    finally:
        dest_conn.close()
        source_conn.close()


def backup(db_path: Path, storage_path: Path, backup_root: Path) -> Path:
    """Creates `backup_root/xerama-backup-<UTC timestamp>/` containing a
    consistent DB snapshot, a full copy of the asset storage directory,
    and a `manifest.json` (sha256 of every file) for later integrity
    verification. Returns the new backup directory's path."""
    if not db_path.is_file():
        raise FileNotFoundError(f"database file not found: {db_path}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest_dir = backup_root / f"xerama-backup-{timestamp}"
    dest_dir.mkdir(parents=True, exist_ok=False)

    dest_db_path = dest_dir / DB_BACKUP_FILENAME
    _backup_sqlite_db(db_path, dest_db_path)

    dest_storage_path = dest_dir / STORAGE_BACKUP_DIRNAME
    if storage_path.is_dir():
        shutil.copytree(storage_path, dest_storage_path)
    else:
        dest_storage_path.mkdir(parents=True)

    files: dict[str, str] = {}
    for path in sorted(dest_dir.rglob("*")):
        if path.is_file() and path.name != MANIFEST_FILENAME:
            files[path.relative_to(dest_dir).as_posix()] = _sha256_file(path)

    manifest = BackupManifest(
        created_at=datetime.now(timezone.utc).isoformat(),
        source_db_path=str(db_path),
        source_storage_path=str(storage_path),
        files=files,
    )
    (dest_dir / MANIFEST_FILENAME).write_text(json.dumps(manifest.__dict__, indent=2))

    return dest_dir


def verify(backup_dir: Path) -> list[str]:
    """Recomputes every file's hash and compares it against the
    manifest. Returns a list of mismatch/missing-file descriptions -
    empty means the backup is intact."""
    manifest_path = backup_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return [f"no {MANIFEST_FILENAME} found in {backup_dir}"]
    manifest = json.loads(manifest_path.read_text())

    problems: list[str] = []
    for relative_path, expected_hash in manifest["files"].items():
        file_path = backup_dir / relative_path
        if not file_path.is_file():
            problems.append(f"missing file: {relative_path}")
            continue
        actual_hash = _sha256_file(file_path)
        if actual_hash != expected_hash:
            problems.append(f"hash mismatch: {relative_path} (expected {expected_hash}, got {actual_hash})")
    return problems


def restore(backup_dir: Path, target_db_path: Path, target_storage_path: Path) -> None:
    """Verifies every file's hash against the manifest first - raises
    `BackupIntegrityError` and restores *nothing* if anything doesn't
    match, rather than partially restoring from a corrupt backup."""
    problems = verify(backup_dir)
    if problems:
        raise BackupIntegrityError(
            f"backup at {backup_dir} failed integrity verification: {'; '.join(problems)}"
        )

    target_db_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_dir / DB_BACKUP_FILENAME, target_db_path)

    if target_storage_path.exists():
        shutil.rmtree(target_storage_path)
    shutil.copytree(backup_dir / STORAGE_BACKUP_DIRNAME, target_storage_path)


def _sqlite_path_from_url(database_url: str) -> Path:
    prefix = "sqlite+aiosqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError(
            f"backup.py only supports local SQLite ({prefix}...) - got {database_url!r}. "
            "A hosted PostgreSQL deployment should use pg_dump/pg_basebackup instead "
            "(see docs/DEPLOYMENT.md)."
        )
    return Path(database_url[len(prefix) :])


def _main(argv: list[str] | None = None) -> int:
    from xerama.config import get_settings

    parser = argparse.ArgumentParser(description="Xerama local backup/restore (MODULE-077).")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup_parser = subparsers.add_parser("backup", help="Create a new backup.")
    backup_parser.add_argument("--backup-dir", default="./backups", help="Where to write the backup.")

    verify_parser = subparsers.add_parser("verify", help="Verify a backup's integrity.")
    verify_parser.add_argument("backup_dir", help="Path to a xerama-backup-* directory.")

    restore_parser = subparsers.add_parser("restore", help="Restore from a backup.")
    restore_parser.add_argument("backup_dir", help="Path to a xerama-backup-* directory.")

    args = parser.parse_args(argv)
    settings = get_settings()
    db_path = _sqlite_path_from_url(settings.database_url)
    storage_path = Path(settings.asset_storage_path)

    if args.command == "backup":
        dest = backup(db_path, storage_path, Path(args.backup_dir))
        print(f"Backup created at {dest}")
    elif args.command == "verify":
        problems = verify(Path(args.backup_dir))
        if problems:
            print("Backup integrity check FAILED:")
            for problem in problems:
                print(f"  - {problem}")
            return 1
        print("Backup integrity check passed - every file matches its manifest hash.")
    elif args.command == "restore":
        restore(Path(args.backup_dir), db_path, storage_path)
        print(f"Restored {args.backup_dir} to {db_path} and {storage_path}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
