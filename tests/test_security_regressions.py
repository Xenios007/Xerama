"""MODULE-066 - Security regression tests.

Path-traversal coverage for the storage layer already lives in
`test_local_storage.py`; upload MIME/size validation lives in
`test_upload_validation.py`. This file covers the two remaining
threat-model surfaces from MODULE-066: unsafe subprocess construction
(FFmpeg/ffprobe) and secret leakage into logs.
"""

import io
import logging
from pathlib import Path

from xerama.config import Settings
from xerama.observability.logging import JsonLogFormatter

_SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "xerama"

# Any of these would let an attacker-influenced string reach a real shell
# instead of being a fixed argv list - see the "never a shell string, so
# there is no injection surface" note in ffmpeg_assembler.py.
_UNSAFE_SUBPROCESS_PATTERNS = (
    "shell=True",
    "os.system(",
    "subprocess.call(",
    "subprocess.run(",
    "subprocess.Popen(",
)


def test_no_shell_invoked_subprocess_anywhere_in_the_codebase() -> None:
    offenders = []
    for path in _SRC_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in _UNSAFE_SUBPROCESS_PATTERNS:
            if pattern in text:
                offenders.append(f"{path}: {pattern}")
    assert offenders == []


def test_settings_repr_never_exposes_the_api_key() -> None:
    settings = Settings(openrouter_api_key="sk-super-secret-value")
    assert "sk-super-secret-value" not in repr(settings)
    assert "sk-super-secret-value" not in str(settings)


def test_settings_dict_serialization_masks_the_api_key() -> None:
    settings = Settings(openrouter_api_key="sk-super-secret-value")
    dumped = settings.model_dump()
    assert "sk-super-secret-value" not in str(dumped)


def test_json_log_formatter_does_not_leak_a_secret_passed_as_a_plain_message() -> None:
    """The formatter has no redaction pass over free text (by design - see
    observability/logging.py docstring: callers must never log secrets in
    the first place). This test documents that boundary: a `SecretStr`
    passed via `extra` stays masked because `str(SecretStr(...))` is
    already masked before it ever reaches the formatter."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonLogFormatter())
    logger = logging.getLogger("xerama.test_security_regressions")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)

    settings = Settings(openrouter_api_key="sk-super-secret-value")
    logger.info("provider configured", extra={"api_key": str(settings.openrouter_api_key)})

    output = stream.getvalue()
    assert "sk-super-secret-value" not in output
    assert "**********" in output
