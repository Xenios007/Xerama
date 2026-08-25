"""Deterministic multimodal QC checks (MODULE-044) - no vision model, no
credentials, always available. These cover `MediaQCDimension.MEDIA_HEALTH`
(any asset type) and `.DIALOGUE_AUDIO` (audio-specific); the remaining
dimensions (identity/style/continuity/composition/motion) genuinely need a
vision-capable model and go through `providers/media_qc.py:MediaQCProvider`
instead.

Only unambiguous evidence (a zero-byte file, an impossible negative
duration) BLOCKs - there is no real audio/video-duration probe wired up
yet (no `ffprobe`-equivalent dependency), so a *missing* duration/dimension
value is a WARN ("verify manually"), never a BLOCK. See ADR-018 - reasons
and a repair recommendation always accompany the verdict, never one opaque
score.
"""

from xerama.domain.asset import Asset, AssetType
from xerama.domain.enums import QCStatus
from xerama.domain.quality import QCResult


def _aspect_ratio_matches(width: int, height: int, expected: str, tolerance: float = 0.05) -> bool:
    try:
        w_str, h_str = expected.split(":")
        expected_ratio = float(w_str) / float(h_str)
    except (ValueError, ZeroDivisionError):
        return True  # unparseable expected ratio - don't fail the asset over bad input
    if height <= 0:
        return False
    actual_ratio = width / height
    return abs(actual_ratio - expected_ratio) / expected_ratio <= tolerance


def check_media_health(
    asset: Asset,
    expected_duration_seconds: float | None = None,
    expected_aspect_ratio: str | None = None,
    duration_tolerance: float = 0.35,
) -> QCResult:
    """Technical-integrity gate: is the file itself usable? Applies to
    every asset type; image/video-specific and video/audio-specific checks
    only run for the relevant `asset.type`."""

    blocking: list[str] = []
    reasons: list[str] = []

    if asset.size_bytes <= 0:
        blocking.append("asset has zero size_bytes - file is empty or missing")

    if asset.type in (AssetType.IMAGE, AssetType.VIDEO):
        if not asset.width or not asset.height:
            reasons.append(f"{asset.type.value} asset is missing width/height metadata")
        elif expected_aspect_ratio and not _aspect_ratio_matches(
            asset.width, asset.height, expected_aspect_ratio
        ):
            reasons.append(
                f"asset aspect ratio {asset.width}:{asset.height} does not match expected "
                f"{expected_aspect_ratio}"
            )

    if asset.type in (AssetType.VIDEO, AssetType.AUDIO):
        if asset.duration_seconds is None:
            reasons.append(f"{asset.type.value} asset is missing duration_seconds metadata")
        elif asset.duration_seconds <= 0:
            blocking.append(f"{asset.type.value} asset has a non-positive duration_seconds")
        elif expected_duration_seconds is not None:
            delta = abs(asset.duration_seconds - expected_duration_seconds)
            if delta > duration_tolerance * max(expected_duration_seconds, 0.01):
                reasons.append(
                    f"duration_seconds={asset.duration_seconds} deviates from expected "
                    f"{expected_duration_seconds} by more than {duration_tolerance:.0%}"
                )

    all_reasons = blocking + reasons
    status = QCStatus.BLOCK if blocking else (QCStatus.WARN if reasons else QCStatus.PASS)
    score = 0.0 if status == QCStatus.BLOCK else max(0.0, 10.0 - 2 * len(all_reasons))
    return QCResult(
        gate="media_health",
        status=status,
        score=score,
        reasons=all_reasons,
        repair_recommendation=(
            "Regenerate or re-upload the asset - the file is empty/corrupt or has an impossible "
            "duration."
            if blocking
            else ("Verify the source generation parameters match the shot's requirements." if reasons else "")
        ),
    )


def check_dialogue_audio(
    asset: Asset,
    expected_duration_seconds: float | None = None,
    duration_tolerance: float = 0.35,
) -> QCResult:
    """Dialogue-specific gate, additive to `check_media_health`: does this
    audio take plausibly match the shot's scripted dialogue timing?"""

    blocking: list[str] = []
    reasons: list[str] = []

    if asset.duration_seconds is not None and asset.duration_seconds < 0:
        blocking.append(f"audio asset has a negative duration_seconds={asset.duration_seconds}")
    elif asset.duration_seconds is None:
        reasons.append(
            "audio asset has no measured duration_seconds - no real audio-duration probe is wired "
            "up yet, verify manually"
        )
    elif expected_duration_seconds is not None:
        delta = abs(asset.duration_seconds - expected_duration_seconds)
        if delta > duration_tolerance * max(expected_duration_seconds, 0.01):
            reasons.append(
                f"audio duration_seconds={asset.duration_seconds} deviates from the shot's "
                f"expected {expected_duration_seconds}s by more than {duration_tolerance:.0%}"
            )

    all_reasons = blocking + reasons
    status = QCStatus.BLOCK if blocking else (QCStatus.WARN if reasons else QCStatus.PASS)
    score = 0.0 if status == QCStatus.BLOCK else max(0.0, 10.0 - 3 * len(all_reasons))
    return QCResult(
        gate="dialogue_audio",
        status=status,
        score=score,
        reasons=all_reasons,
        repair_recommendation=(
            "Regenerate the dialogue take - its duration is impossible."
            if blocking
            else ("Confirm the voice provider's pacing matches the script timing." if reasons else "")
        ),
    )
