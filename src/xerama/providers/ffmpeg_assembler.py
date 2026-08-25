"""Real `EpisodeAssembler` backed by FFmpeg subprocesses (MODULE-046).

Not exercised by the test suite since no `ffmpeg` binary is assumed
installed in this environment - see `FakeAssembler` for what tests
actually run against (same "optional real adapter" precedent as
`FFmpegFrameExtractor`/`FakeFrameExtractor`, Module 08).

Pipeline (each stage a separate, explicit-argv subprocess - never a shell
string, so there is no injection surface even though clip/track ordering
and counts are caller-controlled):

1. Normalize each clip: trim to its shot duration, scale/pad to the
   output resolution, conform fps - so every clip shares identical
   codec parameters before concatenation.
2. Concatenate the normalized clips via the concat demuxer (`-c copy` -
   safe because every input was just normalized to match).
3. If there are supplemental audio tracks (hybrid dialogue / music / SFX),
   mix them onto the concatenated timeline with `adelay`/`volume`/`amix`,
   normalize loudness with `loudnorm`.
4. If a subtitle asset is given, soft-mux it as an `mov_text` stream.
"""

import asyncio
import shutil
import tempfile
from pathlib import Path

from xerama.domain.assembly import AssemblyPlan


class FFmpegAssemblerError(RuntimeError):
    pass


def ffmpeg_is_available(ffmpeg_path: str = "ffmpeg") -> bool:
    return shutil.which(ffmpeg_path) is not None


def _db_to_volume_filter(gain_db: float) -> str:
    return f"volume={gain_db}dB"


class FFmpegAssembler:
    def __init__(self, ffmpeg_path: str = "ffmpeg") -> None:
        self._ffmpeg_path = ffmpeg_path

    async def _run(self, args: list[str]) -> None:
        process = await asyncio.create_subprocess_exec(
            self._ffmpeg_path,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise FFmpegAssemblerError(
                f"ffmpeg failed (code {process.returncode}): {stderr.decode(errors='replace')}"
            )

    async def assemble(
        self, plan: AssemblyPlan, inputs: dict[str, bytes]
    ) -> tuple[bytes, list[list[str]]]:
        if not plan.clips:
            raise FFmpegAssemblerError("assembly plan has no clips")

        commands: list[list[str]] = []
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            output = plan.output

            normalized_paths: list[Path] = []
            for index, clip in enumerate(plan.clips):
                raw_path = tmp / f"clip_{index}_raw.dat"
                await asyncio.to_thread(raw_path.write_bytes, inputs[clip.asset_id])
                norm_path = tmp / f"clip_{index}_norm.mp4"
                args = [
                    "-y",
                    "-i",
                    str(raw_path),
                    "-t",
                    str(clip.duration_seconds),
                    "-vf",
                    f"scale={output.width}:{output.height}:force_original_aspect_ratio=decrease,"
                    f"pad={output.width}:{output.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={output.fps}",
                    "-c:v",
                    output.video_codec,
                    "-b:v",
                    f"{output.video_bitrate_kbps}k",
                    "-c:a",
                    output.audio_codec,
                    "-b:a",
                    f"{output.audio_bitrate_kbps}k",
                    str(norm_path),
                ]
                await self._run(args)
                commands.append(args)
                normalized_paths.append(norm_path)

            concat_list = tmp / "concat.txt"
            list_text = "\n".join(f"file '{p.as_posix()}'" for p in normalized_paths)
            await asyncio.to_thread(concat_list.write_text, list_text)
            assembled_path = tmp / "assembled.mp4"
            concat_args = [
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c",
                "copy",
                str(assembled_path),
            ]
            await self._run(concat_args)
            commands.append(concat_args)

            current_path = assembled_path
            if plan.audio_tracks:
                track_paths: list[Path] = []
                for index, track in enumerate(plan.audio_tracks):
                    track_path = tmp / f"audio_{index}.dat"
                    await asyncio.to_thread(track_path.write_bytes, inputs[track.asset_id])
                    track_paths.append(track_path)

                mixed_path = tmp / "mixed.mp4"
                filter_parts = []
                mix_labels = ["0:a"]
                for index, track in enumerate(plan.audio_tracks, start=1):
                    delay_ms = round(track.start_seconds * 1000)
                    filter_parts.append(
                        f"[{index}:a]adelay={delay_ms}|{delay_ms},"
                        f"{_db_to_volume_filter(track.gain_db)}[a{index}]"
                    )
                    mix_labels.append(f"a{index}")
                mix_inputs = "".join(f"[{label}]" for label in mix_labels)
                filter_parts.append(
                    f"{mix_inputs}amix=inputs={len(mix_labels)}:duration=first,loudnorm[aout]"
                )
                filter_complex = ";".join(filter_parts)

                mix_args = ["-y", "-i", str(assembled_path)]
                for track_path in track_paths:
                    mix_args += ["-i", str(track_path)]
                mix_args += [
                    "-filter_complex",
                    filter_complex,
                    "-map",
                    "0:v",
                    "-map",
                    "[aout]",
                    "-c:v",
                    "copy",
                    "-c:a",
                    output.audio_codec,
                    str(mixed_path),
                ]
                await self._run(mix_args)
                commands.append(mix_args)
                current_path = mixed_path

            if plan.subtitle_asset_id and plan.subtitle_asset_id in inputs:
                subtitle_path = tmp / "subs.srt"
                await asyncio.to_thread(subtitle_path.write_bytes, inputs[plan.subtitle_asset_id])
                final_path = tmp / "final.mp4"
                subtitle_args = [
                    "-y",
                    "-i",
                    str(current_path),
                    "-i",
                    str(subtitle_path),
                    "-map",
                    "0",
                    "-map",
                    "1",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "copy",
                    "-c:s",
                    "mov_text",
                    str(final_path),
                ]
                await self._run(subtitle_args)
                commands.append(subtitle_args)
                current_path = final_path

            data = await asyncio.to_thread(current_path.read_bytes)
            return data, commands
