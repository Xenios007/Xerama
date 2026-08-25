"""MODULE-077 - backup/restore. "Backup -> delete test copy -> restore
-> integrity verification," the module's own verification bar, run
literally as one test at the bottom of this file.
"""

import sqlite3

import pytest

from xerama.backup import (
    BackupIntegrityError,
    _sqlite_path_from_url,
    backup,
    restore,
    verify,
)


def _make_test_db(path) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO projects VALUES ('P1', 'Blood Sisters')")
    conn.commit()
    conn.close()


def _make_test_storage(path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "ab").mkdir()
    (path / "ab" / "abc123.png").write_bytes(b"fake keyframe bytes")
    (path / "cd").mkdir()
    (path / "cd" / "def456.mp4").write_bytes(b"fake render bytes")


def test_backup_creates_a_manifest_covering_every_file(tmp_path) -> None:
    db_path = tmp_path / "xerama.db"
    storage_path = tmp_path / "storage"
    _make_test_db(db_path)
    _make_test_storage(storage_path)

    backup_dir = backup(db_path, storage_path, tmp_path / "backups")

    assert (backup_dir / "xerama.db").is_file()
    assert (backup_dir / "storage" / "ab" / "abc123.png").is_file()
    assert (backup_dir / "manifest.json").is_file()

    import json

    manifest = json.loads((backup_dir / "manifest.json").read_text())
    assert "xerama.db" in manifest["files"]
    assert "storage/ab/abc123.png" in manifest["files"]
    assert "storage/cd/def456.mp4" in manifest["files"]


def test_backup_produces_a_real_independent_sqlite_snapshot(tmp_path) -> None:
    """The backed-up DB is a genuinely separate, openable SQLite file -
    not a reference to the original."""
    db_path = tmp_path / "xerama.db"
    storage_path = tmp_path / "storage"
    _make_test_db(db_path)
    _make_test_storage(storage_path)

    backup_dir = backup(db_path, storage_path, tmp_path / "backups")

    conn = sqlite3.connect(str(backup_dir / "xerama.db"))
    rows = conn.execute("SELECT name FROM projects WHERE id = 'P1'").fetchall()
    conn.close()
    assert rows == [("Blood Sisters",)]


def test_backup_raises_for_a_missing_database(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        backup(tmp_path / "does-not-exist.db", tmp_path / "storage", tmp_path / "backups")


def test_verify_passes_on_an_untouched_backup(tmp_path) -> None:
    db_path = tmp_path / "xerama.db"
    storage_path = tmp_path / "storage"
    _make_test_db(db_path)
    _make_test_storage(storage_path)
    backup_dir = backup(db_path, storage_path, tmp_path / "backups")

    assert verify(backup_dir) == []


def test_verify_detects_a_tampered_file(tmp_path) -> None:
    db_path = tmp_path / "xerama.db"
    storage_path = tmp_path / "storage"
    _make_test_db(db_path)
    _make_test_storage(storage_path)
    backup_dir = backup(db_path, storage_path, tmp_path / "backups")

    (backup_dir / "storage" / "ab" / "abc123.png").write_bytes(b"corrupted!")

    problems = verify(backup_dir)
    assert len(problems) == 1
    assert "storage/ab/abc123.png" in problems[0]


def test_verify_detects_a_missing_file(tmp_path) -> None:
    db_path = tmp_path / "xerama.db"
    storage_path = tmp_path / "storage"
    _make_test_db(db_path)
    _make_test_storage(storage_path)
    backup_dir = backup(db_path, storage_path, tmp_path / "backups")

    (backup_dir / "storage" / "ab" / "abc123.png").unlink()

    problems = verify(backup_dir)
    assert any("missing file" in p for p in problems)


def test_restore_refuses_a_backup_that_fails_verification(tmp_path) -> None:
    db_path = tmp_path / "xerama.db"
    storage_path = tmp_path / "storage"
    _make_test_db(db_path)
    _make_test_storage(storage_path)
    backup_dir = backup(db_path, storage_path, tmp_path / "backups")
    (backup_dir / "storage" / "ab" / "abc123.png").write_bytes(b"corrupted!")

    with pytest.raises(BackupIntegrityError):
        restore(backup_dir, tmp_path / "restored.db", tmp_path / "restored-storage")

    # Nothing was restored - not even the still-valid files.
    assert not (tmp_path / "restored.db").exists()


def test_sqlite_path_from_url_rejects_non_sqlite_urls() -> None:
    with pytest.raises(ValueError):
        _sqlite_path_from_url("postgresql+asyncpg://user:pass@host/db")


def test_sqlite_path_from_url_extracts_the_file_path() -> None:
    assert _sqlite_path_from_url("sqlite+aiosqlite:///./xerama.db") == __import__("pathlib").Path(
        "./xerama.db"
    )


# --- the module's own verification bar, run literally ----------------------


def test_backup_delete_restore_integrity_round_trip(tmp_path) -> None:
    """"Backup -> delete test copy -> restore -> integrity verification" -
    MODULE-077's own "Verification" line, as one continuous test."""
    original_db_path = tmp_path / "live" / "xerama.db"
    original_storage_path = tmp_path / "live" / "storage"
    original_db_path.parent.mkdir(parents=True)
    _make_test_db(original_db_path)
    _make_test_storage(original_storage_path)

    # 1. Backup.
    backup_dir = backup(original_db_path, original_storage_path, tmp_path / "backups")

    # 2. Delete the "test copy" - simulate local failure/operator error
    #    by wiping the live DB and asset store entirely.
    original_db_path.unlink()
    import shutil

    shutil.rmtree(original_storage_path)
    assert not original_db_path.exists()
    assert not original_storage_path.exists()

    # 3. Restore.
    restore(backup_dir, original_db_path, original_storage_path)

    # 4. Integrity verification - the restored project is genuinely
    #    usable, not just present as files.
    assert original_db_path.is_file()
    conn = sqlite3.connect(str(original_db_path))
    rows = conn.execute("SELECT name FROM projects WHERE id = 'P1'").fetchall()
    conn.close()
    assert rows == [("Blood Sisters",)]

    assert (original_storage_path / "ab" / "abc123.png").read_bytes() == b"fake keyframe bytes"
    assert (original_storage_path / "cd" / "def456.mp4").read_bytes() == b"fake render bytes"

    # The restored artifacts still match the backup's own manifest -
    # restoring didn't silently corrupt anything on the way out either.
    assert verify(backup_dir) == []
