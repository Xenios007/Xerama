"""Episode assembly contracts (MODULE-046).

The deterministic instructions FFmpeg needs to build one episode timeline
from already-accepted assets, plus a reproducible record of exactly what
was consumed and produced (ADR-025 - "FFmpeg/ffprobe is the deterministic
finishing layer"; no generative AI anywhere in this module).
"""

from pydantic import BaseModel, Field


class ClipSegment(BaseModel):
    """One shot's accepted video take, positioned in the assembled
    episode timeline. `start_seconds` is the cumulative offset (every
    preceding shot's `duration_seconds` summed), matching
    `pipeline/subtitle_generation.py`'s existing timing convention so
    subtitle cues and assembled clips agree on the same timeline."""

    scene_number: int
    shot_number: int
    asset_id: str
    duration_seconds: float
    start_seconds: float


class AudioTrackSegment(BaseModel):
    """A supplemental audio layer mixed on top of each clip's own
    embedded audio - never a replacement for it. Only `hybrid`-mode
    dialogue (native ambience + a separate controlled TTS layer) and
    music/SFX cues produce these; `native` and `tts_lipsync` dialogue is
    already baked into the clip itself (the lip-sync provider muxes its
    own audio), so no separate track is needed for those modes."""

    kind: str  # "dialogue" | "music" | "sfx"
    asset_id: str
    start_seconds: float
    end_seconds: float
    gain_db: float = 0.0


class OutputSpec(BaseModel):
    """Deterministic finishing/encode settings. Defaults match ADR-015's
    vertical-first target; MODULE-048 layers export-profile validation on
    top rather than redefining these."""

    fps: int = 30
    width: int = 1080
    height: int = 1920
    aspect_ratio: str = "9:16"
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    video_bitrate_kbps: int = 4000
    audio_bitrate_kbps: int = 192


class AssemblyPlan(BaseModel):
    """Pure data - what to render. Produced by
    `pipeline/assembly_plan_builder.py`, consumed by an `EpisodeAssembler`.
    Two calls with the same inputs always produce the same plan
    ("reproducible render manifest")."""

    episode_id: str
    clips: list[ClipSegment] = Field(default_factory=list)
    audio_tracks: list[AudioTrackSegment] = Field(default_factory=list)
    subtitle_asset_id: str | None = None
    output: OutputSpec = Field(default_factory=OutputSpec)
    total_duration_seconds: float = 0.0


class RenderManifest(BaseModel):
    """The audit trail a render produces - what plan was used, exactly
    which asset content-hashes fed it (so a render can be verified or
    reproduced later even if an asset row is later superseded), and the
    actual FFmpeg invocations run. Never regenerated/mutated after a
    render completes - persisted verbatim as part of the output asset's
    provenance."""

    plan: AssemblyPlan
    input_content_hashes: dict[str, str] = Field(default_factory=dict)
    ffmpeg_commands: list[list[str]] = Field(default_factory=list)
    output_duration_seconds: float = 0.0
    warnings: list[str] = Field(default_factory=list)
