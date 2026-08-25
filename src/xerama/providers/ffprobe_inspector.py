"""Real `MediaInspector` backed by an `ffprobe` subprocess (MODULE-048).

Not exercised by the test suite since no `ffprobe` binary is assumed
installed in this environment - see `FakeMediaInspector` for what tests
actually run against (same "optional real adapter" precedent as
`FFmpegFrameExtractor`/`FFmpegAssembler`).
"""

import asyncio
import json
import tempfile
from pathlib import Path

from xerama.domain.export import MediaProbeResult


class FFprobeInspector:
    def __init__(self, ffprobe_path: str = "ffprobe") -> None:
        self._ffprobe_path = ffprobe_path

    async def inspect(self, data: bytes) -> MediaProbeResult:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "in.mp4"
            await asyncio.to_thread(path.write_bytes, data)

            process = await asyncio.create_subprocess_exec(
                self._ffprobe_path,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                return MediaProbeResult(ok=False, error=stderr.decode(errors="replace"))

            try:
                payload = json.loads(stdout)
            except (ValueError, UnicodeDecodeError) as exc:
                return MediaProbeResult(ok=False, error=f"unparseable ffprobe output: {exc}")

            fmt = payload.get("format", {})
            streams = payload.get("streams", [])
            video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

            duration_raw = fmt.get("duration")
            return MediaProbeResult(
                ok=True,
                duration_seconds=float(duration_raw) if duration_raw is not None else None,
                width=video_stream.get("width") if video_stream else None,
                height=video_stream.get("height") if video_stream else None,
                video_codec=video_stream.get("codec_name", "") if video_stream else "",
                audio_codec=audio_stream.get("codec_name", "") if audio_stream else "",
                has_video_stream=video_stream is not None,
                has_audio_stream=audio_stream is not None,
            )
