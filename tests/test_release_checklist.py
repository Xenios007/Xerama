"""MODULE-080 - a light, fast unit test for the release checklist's
pure/self-contained check (no subprocess, so safe to run from inside
the very test suite it's adjacent to). The heavier subprocess-based
checks (full pytest run, frontend build, smoke test, ...) are verified
by actually running `python scripts/release_checklist.py` by hand - see
docs/RELEASE_NOTES.md's recorded "RELEASE READY" result - not by
re-invoking them recursively from within pytest itself.
"""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_release_checklist():
    spec = importlib.util.spec_from_file_location(
        "release_checklist", REPO_ROOT / "scripts" / "release_checklist.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["release_checklist"] = module
    spec.loader.exec_module(module)
    return module


def test_todo_fixme_sweep_finds_none_in_this_repository() -> None:
    release_checklist = _load_release_checklist()
    result = release_checklist.check_todo_fixme_sweep()
    assert result.passed, result.detail


def test_todo_fixme_sweep_detects_a_planted_marker(tmp_path, monkeypatch) -> None:
    release_checklist = _load_release_checklist()
    fake_src = tmp_path / "src" / "xerama"
    fake_src.mkdir(parents=True)
    (fake_src / "planted.py").write_text("# TODO: this should be caught\n")
    monkeypatch.setattr(release_checklist, "REPO_ROOT", tmp_path)

    result = release_checklist.check_todo_fixme_sweep()
    assert result.passed is False
    assert "planted.py" in result.detail
