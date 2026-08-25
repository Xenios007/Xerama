"""Vertical export contracts (MODULE-048).

An `ExportProfile` names a target `OutputSpec` (MODULE-046) so callers
pick a profile, not raw codec/bitrate numbers - "configurable codec/
bitrate/FPS/audio settings" without a new parallel settings shape.
"""

from pydantic import BaseModel, Field

from xerama.domain.assembly import OutputSpec


class ExportProfile(BaseModel):
    name: str
    output: OutputSpec = Field(default_factory=OutputSpec)


# ADR-015 vertical-first default - 1080x1920 when source quality allows,
# matching MODULE-048's "Default 9:16, target 1080x1920" requirement
# exactly with `OutputSpec`'s own defaults.
VERTICAL_1080_1920 = ExportProfile(name="vertical_1080x1920", output=OutputSpec())


class MediaProbeResult(BaseModel):
    """What `MediaInspector.inspect` reports about a rendered file -
    ffprobe's view of ground truth, independent of what the render
    *intended* to produce."""

    ok: bool = True
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    video_codec: str = ""
    audio_codec: str = ""
    has_video_stream: bool = False
    has_audio_stream: bool = False
    error: str = ""
