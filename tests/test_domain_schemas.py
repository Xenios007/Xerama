import pytest
from pydantic import ValidationError

from xerama.domain.enums import CliffhangerType, JudgeDecision
from xerama.domain.episode import Cliffhanger, EpisodeOutline
from xerama.domain.quality import QualityScore
from xerama.domain.story import CandidateScore, JudgeCriteria, JudgeResult


def test_judge_result_round_trip() -> None:
    result = JudgeResult(
        decision=JudgeDecision.MERGE,
        candidate_a=CandidateScore(score=7.5, strengths=["hook"], weaknesses=["pacing"]),
        candidate_b=CandidateScore(score=8.0, strengths=["cast"]),
        criteria=JudgeCriteria(
            hook=8,
            emotional_intensity=7,
            conflict=7,
            originality=6,
            serial_potential=8,
            reversal_potential=7,
            cliffhanger_potential=9,
            production_feasibility=8,
            character_potential=7,
        ),
        reason="B has a stronger cast but A's hook is better.",
    )
    dumped = result.model_dump_json()
    restored = JudgeResult.model_validate_json(dumped)
    assert restored.decision == JudgeDecision.MERGE
    assert restored.candidate_a.score == 7.5
    assert restored.merge_instructions.take_from_a == []


def test_judge_criteria_rejects_out_of_range_score() -> None:
    with pytest.raises(ValidationError):
        JudgeCriteria(
            hook=11,
            emotional_intensity=5,
            conflict=5,
            originality=5,
            serial_potential=5,
            reversal_potential=5,
            cliffhanger_potential=5,
            production_feasibility=5,
            character_potential=5,
        )


def test_quality_score_bounds() -> None:
    with pytest.raises(ValidationError):
        QualityScore(
            hook=5,
            conflict=5,
            emotional_intensity=5,
            information_gap=5,
            reversal=5,
            cliffhanger=5,
            character_consistency=5,
            continuity=5,
            serial_progress=5,
            originality=5,
            production_feasibility=5,
            repetition_risk=5,
            overall=-1,
        )


def test_episode_outline_requires_cliffhanger() -> None:
    with pytest.raises(ValidationError):
        EpisodeOutline(
            episode_number=1,
            objective="find the truth",
            opening_hook="a scream in the dark",
            stakes="her freedom",
            conflict="sister vs. sister",
            turn="the letter was a forgery",
            reveal="he was never who he claimed",
            duration_target_seconds=75,
        )  # missing `cliffhanger`


def test_episode_outline_valid() -> None:
    outline = EpisodeOutline(
        episode_number=1,
        objective="find the truth",
        opening_hook="a scream in the dark",
        stakes="her freedom",
        conflict="sister vs. sister",
        turn="the letter was a forgery",
        reveal="he was never who he claimed",
        duration_target_seconds=75,
        cliffhanger=Cliffhanger(type=CliffhangerType.IDENTITY_REVEAL, event="the mask comes off"),
    )
    assert outline.cliffhanger.type == CliffhangerType.IDENTITY_REVEAL
