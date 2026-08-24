"""Deterministic subtitle readability validation (MODULE-039).

"Respect 9:16 safe areas, line length and reading speed." Same pass/warn
shape as `DirectorValidator` (ADR-018) but for the subtitle track.
"""

from xerama.domain.enums import QCStatus
from xerama.domain.quality import QCResult
from xerama.domain.subtitle import SubtitleCue
from xerama.pipeline.subtitle_generation import (
    MAX_CHARS_PER_LINE,
    MAX_LINES,
    MAX_READING_CHARS_PER_SECOND,
)


class SubtitleValidator:
    def check_readability(self, cues: list[SubtitleCue]) -> QCResult:
        reasons: list[str] = []
        for cue in cues:
            duration = cue.end_seconds - cue.start_seconds
            label = f"scene {cue.scene_number} shot {cue.shot_number}"
            if duration <= 0:
                reasons.append(f"{label}: cue has non-positive duration ({duration}s)")
                continue
            chars_per_second = len(cue.text) / duration
            if chars_per_second > MAX_READING_CHARS_PER_SECOND:
                reasons.append(
                    f"{label}: reading speed {chars_per_second:.1f} chars/s exceeds "
                    f"{MAX_READING_CHARS_PER_SECOND} chars/s"
                )
            if len(cue.lines) > MAX_LINES:
                reasons.append(f"{label}: {len(cue.lines)} lines exceeds the {MAX_LINES}-line safe area")
            for line in cue.lines:
                if len(line) > MAX_CHARS_PER_LINE:
                    reasons.append(
                        f"{label}: line {line!r} ({len(line)} chars) exceeds {MAX_CHARS_PER_LINE} chars"
                    )

        status = QCStatus.WARN if reasons else QCStatus.PASS
        score = max(0.0, 10.0 - len(reasons))
        return QCResult(
            gate="subtitle_readability",
            status=status,
            score=score,
            reasons=reasons,
            repair_recommendation=(
                "Shorten flagged lines/cues or extend their duration to meet reading-speed guidance."
                if reasons
                else ""
            ),
        )
