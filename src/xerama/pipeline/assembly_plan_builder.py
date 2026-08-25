"""Deterministic assembly-plan construction (MODULE-046).

Walks the approved shot plan in scene/shot order (same cumulative-offset
convention as `pipeline/subtitle_generation.py:cues_from_shot_plan`) and
pulls in only *approved* production assets - never a draft/rejected take.
No LLM call, no randomness: the same approved shot plan + approved
takes/cues always produces the same `AssemblyPlan`.
"""

from xerama.domain.assembly import AssemblyPlan, AudioTrackSegment, ClipSegment, OutputSpec
from xerama.domain.audio_production import ShotAudioProduction
from xerama.domain.enums import AudioMode
from xerama.domain.music import MusicCue
from xerama.domain.scene import EpisodeShotPlan
from xerama.domain.sound_effect import SoundEffectCue
from xerama.domain.video_production import ShotVideoProduction


class IncompleteProductionError(ValueError):
    """Raised when a shot required by the approved shot plan has no
    approved production asset yet - assembling anyway would silently
    render an incomplete episode."""


def build_assembly_plan(
    episode_id: str,
    plan: EpisodeShotPlan,
    video_productions: list[ShotVideoProduction],
    audio_productions: list[ShotAudioProduction],
    music_cues: list[MusicCue],
    sfx_cues: list[SoundEffectCue],
    subtitle_asset_id: str | None = None,
    output: OutputSpec | None = None,
) -> AssemblyPlan:
    video_by_shot = {(p.scene_number, p.shot_number): p for p in video_productions}
    audio_by_shot = {(p.scene_number, p.shot_number): p for p in audio_productions}

    ordered_shots = sorted(
        ((scene.scene_number, shot) for scene in plan.scenes for shot in scene.shots),
        key=lambda pair: (pair[0], pair[1].shot_number),
    )

    clips: list[ClipSegment] = []
    audio_tracks: list[AudioTrackSegment] = []
    cursor = 0.0
    for scene_number, shot in ordered_shots:
        key = (scene_number, shot.shot_number)
        video_production = video_by_shot.get(key)
        if (
            video_production is None
            or video_production.status != "approved"
            or not video_production.approved_take_asset_id
        ):
            raise IncompleteProductionError(
                f"scene {scene_number} shot {shot.shot_number} has no approved video take"
            )
        clips.append(
            ClipSegment(
                scene_number=scene_number,
                shot_number=shot.shot_number,
                asset_id=video_production.approved_take_asset_id,
                duration_seconds=shot.duration_seconds,
                start_seconds=cursor,
            )
        )

        # `native`/`tts_lipsync` dialogue is already embedded in the video
        # take itself (a lip-synced clip's provider muxes its own audio) -
        # only `hybrid` needs a separate mixed-in dialogue layer.
        if shot.audio_mode == AudioMode.HYBRID:
            audio_production = audio_by_shot.get(key)
            if (
                audio_production is None
                or audio_production.status != "approved"
                or not audio_production.approved_take_asset_id
            ):
                raise IncompleteProductionError(
                    f"scene {scene_number} shot {shot.shot_number} is hybrid audio_mode but has no "
                    "approved dialogue take"
                )
            audio_tracks.append(
                AudioTrackSegment(
                    kind="dialogue",
                    asset_id=audio_production.approved_take_asset_id,
                    start_seconds=cursor,
                    end_seconds=cursor + shot.duration_seconds,
                )
            )

        cursor += shot.duration_seconds

    for cue in music_cues:
        if cue.asset_id and cue.status == "approved":
            audio_tracks.append(
                AudioTrackSegment(
                    kind="music",
                    asset_id=cue.asset_id,
                    start_seconds=cue.start_seconds,
                    end_seconds=cue.end_seconds,
                    gain_db=-abs(cue.ducking_db),
                )
            )

    for cue in sfx_cues:
        if cue.asset_id and cue.status == "approved":
            audio_tracks.append(
                AudioTrackSegment(
                    kind="sfx",
                    asset_id=cue.asset_id,
                    start_seconds=cue.start_seconds,
                    end_seconds=cue.end_seconds,
                    gain_db=cue.gain_db,
                )
            )

    return AssemblyPlan(
        episode_id=episode_id,
        clips=clips,
        audio_tracks=audio_tracks,
        subtitle_asset_id=subtitle_asset_id,
        output=output or OutputSpec(),
        total_duration_seconds=cursor,
    )
