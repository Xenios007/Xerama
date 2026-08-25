"""Deterministic vertical-export validation (MODULE-048).

Combines ffprobe ground truth (duration/aspect/streams/corruption) with
MODULE-039's existing subtitle-readability check into one pass/warn/block
verdict (ADR-018) - reuses `SubtitleValidator` rather than a second safe-
area implementation. Only unambiguous evidence (ffprobe itself failing, no
video stream at all) BLOCKs; a value that couldn't be measured (no real
ffprobe wired up, or a placeholder render) WARNs, same precedent as
`pipeline/media_qc_checks.py`.
"""

from xerama.domain.assembly import OutputSpec
from xerama.domain.enums import QCStatus
from xerama.domain.export import MediaProbeResult
from xerama.domain.quality import QCResult
from xerama.domain.subtitle import SubtitleCue
from xerama.pipeline.subtitle_validators import SubtitleValidator


def validate_export(
    probe: MediaProbeResult,
    expected_output: OutputSpec,
    expected_duration_seconds: float | None = None,
    subtitle_cues: list[SubtitleCue] | None = None,
    duration_tolerance: float = 0.1,
) -> QCResult:
    blocking: list[str] = []
    reasons: list[str] = []

    if not probe.ok:
        blocking.append(f"ffprobe could not read the export - {probe.error or 'corrupt/unreadable file'}")
    else:
        if not probe.has_video_stream:
            blocking.append("export has no video stream")
        if not probe.has_audio_stream:
            reasons.append("export has no audio stream")

        if probe.duration_seconds is None:
            reasons.append("duration could not be measured (no real ffprobe wired up yet)")
        elif expected_duration_seconds is not None:
            delta = abs(probe.duration_seconds - expected_duration_seconds)
            if delta > duration_tolerance * max(expected_duration_seconds, 0.01):
                reasons.append(
                    f"duration {probe.duration_seconds}s does not match the expected "
                    f"{expected_duration_seconds}s"
                )

        if probe.width is None or probe.height is None:
            reasons.append("resolution could not be measured (no real ffprobe wired up yet)")
        elif (probe.width, probe.height) != (expected_output.width, expected_output.height):
            reasons.append(
                f"resolution {probe.width}x{probe.height} does not match the target "
                f"{expected_output.width}x{expected_output.height}"
            )

    if subtitle_cues:
        subtitle_result = SubtitleValidator().check_readability(subtitle_cues)
        reasons.extend(f"subtitle safe-area: {r}" for r in subtitle_result.reasons)

    all_reasons = blocking + reasons
    status = QCStatus.BLOCK if blocking else (QCStatus.WARN if reasons else QCStatus.PASS)
    score = 0.0 if status == QCStatus.BLOCK else max(0.0, 10.0 - 1.5 * len(all_reasons))
    return QCResult(
        gate="vertical_export",
        status=status,
        score=score,
        reasons=all_reasons,
        repair_recommendation=(
            "Re-render the episode - the export file is unusable."
            if blocking
            else ("Verify encode settings and subtitle timing against the target export profile." if reasons else "")
        ),
    )
