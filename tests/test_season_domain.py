import pytest
from pydantic import ValidationError

from xerama.domain.enums import AwarenessStatus, CliffhangerType, ThreadStatus
from xerama.domain.season import (
    EpisodeAssignment,
    Mystery,
    Promise,
    RevealMilestone,
    SeasonAct,
    SeasonPlan,
)


def _minimal_plan(**overrides) -> dict:
    base = dict(
        series_title="Blood Sisters",
        episode_count=1,
        acts=[
            SeasonAct(
                act_number=1, name="Setup", start_episode=1, end_episode=1, objective="intro"
            )
        ],
        episode_assignments=[
            EpisodeAssignment(
                episode_number=1,
                act_number=1,
                objective="find the letter",
                escalation_level=3,
            )
        ],
    )
    base.update(overrides)
    return base


def test_season_plan_round_trip() -> None:
    plan = SeasonPlan(**_minimal_plan())
    restored = SeasonPlan.model_validate_json(plan.model_dump_json())
    assert restored.episode_count == 1
    assert restored.episode_assignments[0].objective == "find the letter"


def test_season_plan_requires_episode_assignments() -> None:
    data = _minimal_plan()
    del data["episode_assignments"]
    with pytest.raises(ValidationError):
        SeasonPlan(**data)


def test_escalation_level_bounds() -> None:
    with pytest.raises(ValidationError):
        EpisodeAssignment(episode_number=1, act_number=1, objective="x", escalation_level=11)


def test_reveal_milestone_defaults() -> None:
    reveal = RevealMilestone(id="REV_001", description="the letter", planned_episode=1)
    assert reveal.audience_knowledge_before == AwarenessStatus.UNKNOWN
    assert reveal.audience_knowledge_after == AwarenessStatus.KNOWS
    assert reveal.depends_on == []


def test_mystery_and_promise_default_status_open() -> None:
    mystery = Mystery(id="MYS_001", question="who?", introduced_episode=1)
    promise = Promise(id="PROM_001", description="find the truth", setup_episode=1)
    assert mystery.status == ThreadStatus.OPEN
    assert promise.status == ThreadStatus.OPEN


def test_episode_assignment_optional_cliffhanger_type() -> None:
    assignment = EpisodeAssignment(episode_number=1, act_number=1, objective="x", escalation_level=1)
    assert assignment.cliffhanger_type is None

    assignment2 = EpisodeAssignment(
        episode_number=2,
        act_number=1,
        objective="y",
        escalation_level=2,
        cliffhanger_type=CliffhangerType.BETRAYAL,
    )
    assert assignment2.cliffhanger_type == CliffhangerType.BETRAYAL
