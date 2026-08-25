"""Shared timeout-safe subprocess helper (MODULE-070).

`asyncio.subprocess.Process.communicate()` has no timeout of its own - a
malformed/pathological input can hang `ffmpeg`/`ffprobe` indefinitely,
which (Trial 01 runs generation synchronously within the HTTP request -
docs/ARCHITECTURE.md section 14) would hang the request, and the worker
handling it, forever. Every real-subprocess provider
(`ffmpeg_assembler.py`, `ffmpeg_frame_extractor.py`, `ffprobe_inspector.py`)
goes through this one helper so the "kill on timeout, don't just give up
waiting" behavior is written once.
"""

import asyncio


class SubprocessTimeoutError(RuntimeError):
    pass


async def communicate_with_timeout(
    process: asyncio.subprocess.Process, timeout_seconds: float
) -> tuple[bytes, bytes]:
    """Like `process.communicate()`, but kills the process and raises
    `SubprocessTimeoutError` instead of hanging past `timeout_seconds`."""
    try:
        return await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
    except TimeoutError:
        process.kill()
        await process.wait()  # reap - avoid leaving a zombie process behind
        raise SubprocessTimeoutError(
            f"subprocess did not complete within {timeout_seconds:.0f}s and was killed"
        ) from None
