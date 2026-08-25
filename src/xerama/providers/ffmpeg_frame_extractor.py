"""Real `FrameExtractor` backed by an FFmpeg subprocess (Module 08 - "FFmpeg
is acceptable"). Not exercised by the test suite since no `ffmpeg` binary is
assumed to be installed in this environment - see `FakeFrameExtractor` for
what tests actually run against.
"""

import asyncio
import tempfile
from pathlib import Path

from xerama.providers.subprocess_utils import SubprocessTimeoutError, communicate_with_timeout


class FFmpegExtractionError(RuntimeError):
    pass


class FFmpegFrameExtractor:
    def __init__(self, ffmpeg_path: str = "ffmpeg", timeout_seconds: float = 300.0) -> None:
        self._ffmpeg_path = ffmpeg_path
        self._timeout_seconds = timeout_seconds

    async def extract_last_frame(self, video_bytes: bytes) -> bytes:
        with tempfile.TemporaryDirectory() as tmp:
            video_path = Path(tmp) / "in.mp4"
            frame_path = Path(tmp) / "out.png"
            await asyncio.to_thread(video_path.write_bytes, video_bytes)

            process = await asyncio.create_subprocess_exec(
                self._ffmpeg_path,
                "-y",
                "-sseof",
                "-1",
                "-i",
                str(video_path),
                "-update",
                "1",
                "-frames:v",
                "1",
                str(frame_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _, stderr = await communicate_with_timeout(process, self._timeout_seconds)
            except SubprocessTimeoutError as exc:
                raise FFmpegExtractionError(str(exc)) from exc
            if process.returncode != 0 or not frame_path.exists():
                raise FFmpegExtractionError(
                    f"ffmpeg last-frame extraction failed (code {process.returncode}): "
                    f"{stderr.decode(errors='replace')}"
                )
            return await asyncio.to_thread(frame_path.read_bytes)
