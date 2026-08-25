import pytest

from xerama.domain.enums import MediaQCDimension, QCStatus, RepairAction
from xerama.domain.media_qc import MediaQCAttempt
from xerama.pipeline.retake_policy import classify_repair_action
from xerama.services.retake_service import MAX_AUTO_RETAKE_ATTEMPTS, AutomaticRetakeService, RepairPlan


def _attempt(dimension: MediaQCDimension, status: QCStatus, reasons=None) -> MediaQCAttempt:
    return MediaQCAttempt(
        id="A1",
        asset_id="ASSET1",
        dimension=dimension,
        status=status,
        score=0.0 if status == QCStatus.BLOCK else 8.0,
        reasons=reasons or [],
    )


# --- classify_repair_action -------------------------------------------------


def test_classify_identity_block_prefers_stronger_references() -> None:
    attempts = [_attempt(MediaQCDimension.IDENTITY, QCStatus.BLOCK, ["face mismatch"])]
    assert classify_repair_action(attempts) == RepairAction.STRONGER_REFERENCES


def test_classify_style_block_prefers_stronger_references() -> None:
    attempts = [_attempt(MediaQCDimension.STYLE, QCStatus.BLOCK)]
    assert classify_repair_action(attempts) == RepairAction.STRONGER_REFERENCES


def test_classify_composition_block_prefers_prompt_repair() -> None:
    attempts = [_attempt(MediaQCDimension.COMPOSITION, QCStatus.BLOCK)]
    assert classify_repair_action(attempts) == RepairAction.PROMPT_REPAIR


def test_classify_continuity_and_motion_block_prefers_prompt_repair() -> None:
    assert classify_repair_action([_attempt(MediaQCDimension.CONTINUITY, QCStatus.BLOCK)]) == (
        RepairAction.PROMPT_REPAIR
    )
    assert classify_repair_action([_attempt(MediaQCDimension.MOTION, QCStatus.BLOCK)]) == (
        RepairAction.PROMPT_REPAIR
    )


def test_classify_media_health_block_prefers_alternate_provider() -> None:
    attempts = [_attempt(MediaQCDimension.MEDIA_HEALTH, QCStatus.BLOCK)]
    assert classify_repair_action(attempts) == RepairAction.ALTERNATE_PROVIDER


def test_classify_dialogue_audio_block_falls_back_to_full_retake() -> None:
    attempts = [_attempt(MediaQCDimension.DIALOGUE_AUDIO, QCStatus.BLOCK)]
    assert classify_repair_action(attempts) == RepairAction.FULL_RETAKE


def test_classify_prioritizes_identity_over_media_health() -> None:
    attempts = [
        _attempt(MediaQCDimension.MEDIA_HEALTH, QCStatus.BLOCK),
        _attempt(MediaQCDimension.IDENTITY, QCStatus.BLOCK),
    ]
    assert classify_repair_action(attempts) == RepairAction.STRONGER_REFERENCES


def test_classify_ignores_non_blocked_attempts() -> None:
    attempts = [
        _attempt(MediaQCDimension.IDENTITY, QCStatus.WARN),
        _attempt(MediaQCDimension.MEDIA_HEALTH, QCStatus.BLOCK),
    ]
    assert classify_repair_action(attempts) == RepairAction.ALTERNATE_PROVIDER


# --- AutomaticRetakeService --------------------------------------------------


def test_plan_repair_returns_classified_action_under_budget() -> None:
    service = AutomaticRetakeService()
    attempts = [_attempt(MediaQCDimension.COMPOSITION, QCStatus.BLOCK, ["crowded frame"])]
    plan = service.plan_repair(attempts, prior_attempt_count=0)
    assert plan == RepairPlan(action=RepairAction.PROMPT_REPAIR, reasons=["crowded frame"])


def test_plan_repair_escalates_at_budget() -> None:
    service = AutomaticRetakeService()
    attempts = [_attempt(MediaQCDimension.COMPOSITION, QCStatus.BLOCK, ["still bad"])]
    plan = service.plan_repair(attempts, prior_attempt_count=MAX_AUTO_RETAKE_ATTEMPTS)
    assert plan.action == RepairAction.ESCALATE
    assert plan.reasons == ["still bad"]


def test_plan_repair_escalates_past_budget_too() -> None:
    service = AutomaticRetakeService()
    attempts = [_attempt(MediaQCDimension.COMPOSITION, QCStatus.BLOCK)]
    plan = service.plan_repair(attempts, prior_attempt_count=MAX_AUTO_RETAKE_ATTEMPTS + 5)
    assert plan.action == RepairAction.ESCALATE
