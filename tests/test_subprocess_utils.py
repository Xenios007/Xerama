import asyncio
import sys

import pytest

from xerama.providers.subprocess_utils import SubprocessTimeoutError, communicate_with_timeout


async def _spawn(*args: str) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        sys.executable, "-c", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )


async def test_communicate_with_timeout_returns_output_for_a_fast_process() -> None:
    process = await _spawn("import sys; sys.stdout.write('hello')")
    stdout, _ = await communicate_with_timeout(process, timeout_seconds=10.0)
    assert stdout == b"hello"


async def test_communicate_with_timeout_kills_a_hung_process() -> None:
    process = await _spawn("import time; time.sleep(30)")
    with pytest.raises(SubprocessTimeoutError):
        await communicate_with_timeout(process, timeout_seconds=0.2)
    # The process was actually killed, not just abandoned - wait() would
    # hang forever on a still-running process.
    returncode = await asyncio.wait_for(process.wait(), timeout=5.0)
    assert returncode is not None


async def test_communicate_with_timeout_does_not_leave_a_zombie() -> None:
    process = await _spawn("import time; time.sleep(30)")
    with pytest.raises(SubprocessTimeoutError):
        await communicate_with_timeout(process, timeout_seconds=0.2)
    assert process.returncode is not None
