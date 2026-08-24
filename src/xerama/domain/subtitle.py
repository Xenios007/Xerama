"""Subtitle cue domain contract (MODULE-039).

"Generate readable mobile-first subtitles from canonical dialogue/timing."
Cues are derived deterministically from the approved shot plan (Module 03)
- the production-level breakdown that actually carries per-shot duration -
rather than the prose script, which has no timing at all.
"""

from pydantic import BaseModel, Field


class SubtitleCue(BaseModel):
    id: str
    episode_id: str
    scene_number: int
    shot_number: int
    character_id: str | None = None
    language: str = "en"
    text: str
    # Word-wrapped for mobile 9:16 safe areas - see
    # subtitle.py:wrap_subtitle_text. Kept alongside `text` so the raw line
    # is never lost even after wrapping.
    lines: list[str] = Field(default_factory=list)
    start_seconds: float
    end_seconds: float
