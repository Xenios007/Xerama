"""Deterministic subtitle cue generation and SRT export (MODULE-039).

No LLM call, no randomness - subtitles are derived purely from the
approved shot plan's dialogue/duration fields, so regenerating always
produces the same result for the same plan ("keep subtitles deterministic
from approved script/audio timing").
"""

from xerama.domain.scene import EpisodeShotPlan
from xerama.domain.subtitle import SubtitleCue

MAX_CHARS_PER_LINE = 32
MAX_LINES = 2
MAX_READING_CHARS_PER_SECOND = 17.0  # standard subtitle readability guideline


def wrap_subtitle_text(text: str, max_chars_per_line: int = MAX_CHARS_PER_LINE) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > max_chars_per_line:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def cues_from_shot_plan(plan: EpisodeShotPlan, language: str = "en") -> list[dict]:
    """One cue per shot with non-empty dialogue, positioned at its
    cumulative offset in the assembled episode timeline (summing every
    preceding shot's `duration_seconds`, dialogue or not - there is no
    editor/assembly stage yet to derive this from, so this is the only
    currently-available source of truth for episode-level timing)."""
    ordered_shots = sorted(
        ((scene.scene_number, shot) for scene in plan.scenes for shot in scene.shots),
        key=lambda pair: (pair[0], pair[1].shot_number),
    )
    cues: list[dict] = []
    cursor = 0.0
    for scene_number, shot in ordered_shots:
        start_seconds = cursor
        end_seconds = cursor + shot.duration_seconds
        cursor = end_seconds
        if not shot.dialogue.strip():
            continue
        cues.append(
            {
                "scene_number": scene_number,
                "shot_number": shot.shot_number,
                "character_id": shot.character_ids[0] if len(shot.character_ids) == 1 else None,
                "language": language,
                "text": shot.dialogue,
                "lines": wrap_subtitle_text(shot.dialogue),
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
            }
        )
    return cues


def format_srt_timestamp(seconds: float) -> str:
    total_ms = round(seconds * 1000)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def export_srt(cues: list[SubtitleCue]) -> str:
    ordered = sorted(cues, key=lambda c: (c.scene_number, c.shot_number))
    blocks = []
    for index, cue in enumerate(ordered, start=1):
        text = "\n".join(cue.lines) if cue.lines else cue.text
        blocks.append(
            f"{index}\n"
            f"{format_srt_timestamp(cue.start_seconds)} --> {format_srt_timestamp(cue.end_seconds)}\n"
            f"{text}\n"
        )
    return "\n".join(blocks)
