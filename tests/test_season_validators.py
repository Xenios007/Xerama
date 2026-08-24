import copy

import fixtures as fx
from xerama.domain.character import CharacterCast
from xerama.domain.enums import QCStatus
from xerama.domain.season import SeasonPlan
from xerama.pipeline.season_validators import SeasonValidator


def _plan(**mutations) -> SeasonPlan:
    data = copy.deepcopy(fx.season_plan())
    data.update(mutations)
    return SeasonPlan.model_validate(data)


def _cast() -> CharacterCast:
    return CharacterCast.model_validate(fx.cast())


def test_valid_season_plan_passes() -> None:
    result = SeasonValidator().validate(_plan(), _cast())
    assert result.status == QCStatus.PASS
    assert result.score == 10.0
    assert result.reasons == []


def test_missing_episode_assignment_blocks() -> None:
    data = copy.deepcopy(fx.season_plan())
    data["episode_assignments"] = data["episode_assignments"][:2]  # drop episode 3
    result = SeasonValidator().validate(SeasonPlan.model_validate(data), _cast())
    assert result.status == QCStatus.BLOCK
    assert any("missing" in r for r in result.reasons)


def test_duplicate_episode_assignment_blocks() -> None:
    data = copy.deepcopy(fx.season_plan())
    data["episode_assignments"].append(copy.deepcopy(data["episode_assignments"][0]))
    result = SeasonValidator().validate(SeasonPlan.model_validate(data), _cast())
    assert result.status == QCStatus.BLOCK
    assert any("duplicate" in r for r in result.reasons)


def test_reveal_before_mystery_introduced_blocks() -> None:
    data = copy.deepcopy(fx.season_plan())
    data["reveals"][0]["planned_episode"] = 1
    data["mysteries"][0]["introduced_episode"] = 2  # reveal now precedes its own mystery
    result = SeasonValidator().validate(SeasonPlan.model_validate(data), _cast())
    assert result.status == QCStatus.BLOCK
    assert any("before its mystery" in r for r in result.reasons)


def test_reveal_before_dependency_blocks_premature_reveal() -> None:
    data = copy.deepcopy(fx.season_plan())
    # REV_002 depends on REV_001. Push REV_001 later than REV_002 so the
    # dependency is scheduled after the reveal that needs it first.
    data["reveals"][0]["planned_episode"] = 2
    data["reveals"][1]["planned_episode"] = 1
    result = SeasonValidator().validate(SeasonPlan.model_validate(data), _cast())
    assert result.status == QCStatus.BLOCK
    assert any("premature reveal" in r for r in result.reasons)


def test_payoff_before_setup_blocks() -> None:
    data = copy.deepcopy(fx.season_plan())
    data["promises"][0]["setup_episode"] = 3
    data["promises"][0]["payoff_episode"] = 1
    result = SeasonValidator().validate(SeasonPlan.model_validate(data), _cast())
    assert result.status == QCStatus.BLOCK
    assert any("pays off before" in r for r in result.reasons)


def test_resolved_without_payoff_episode_blocks() -> None:
    data = copy.deepcopy(fx.season_plan())
    data["promises"][0]["payoff_episode"] = None
    # status stays "resolved" - inconsistent with no payoff episode.
    result = SeasonValidator().validate(SeasonPlan.model_validate(data), _cast())
    assert result.status == QCStatus.BLOCK
    assert any("no payoff_episode" in r for r in result.reasons)


def test_fully_resolved_season_warns_no_continuation_hook() -> None:
    data = copy.deepcopy(fx.season_plan())
    data["mysteries"][1]["status"] = "resolved"
    data["mysteries"][1]["resolution_episode"] = 3
    result = SeasonValidator().validate(SeasonPlan.model_validate(data), _cast())
    assert result.status == QCStatus.WARN
    assert any("no continuation hook" in r for r in result.reasons)


def test_flat_escalation_warns() -> None:
    data = copy.deepcopy(fx.season_plan())
    for milestone in data["escalation_milestones"]:
        milestone["escalation_level"] = 5
    for assignment in data["episode_assignments"]:
        assignment["escalation_level"] = 5
    result = SeasonValidator().validate(SeasonPlan.model_validate(data), _cast())
    assert result.status == QCStatus.WARN
    assert any("does not trend upward" in r for r in result.reasons)


def test_missing_character_arc_warns() -> None:
    data = copy.deepcopy(fx.season_plan())
    data["character_arc_milestones"] = [
        m for m in data["character_arc_milestones"] if m["character_id"] != "CHAR_002"
    ]
    result = SeasonValidator().validate(SeasonPlan.model_validate(data), _cast())
    assert result.status == QCStatus.WARN
    assert any("CHAR_002" in r for r in result.reasons)


def test_repeated_cliffhanger_type_warns() -> None:
    data = copy.deepcopy(fx.season_plan())
    data["episode_assignments"][1]["cliffhanger_type"] = "discovery"  # same as episode 1
    result = SeasonValidator().validate(SeasonPlan.model_validate(data), _cast())
    assert result.status == QCStatus.WARN
    assert any("repeats the previous episode's cliffhanger type" in r for r in result.reasons)


def test_episode_with_no_progress_warns() -> None:
    data = copy.deepcopy(fx.season_plan())
    data["episode_assignments"][1]["character_milestones"] = []
    result = SeasonValidator().validate(SeasonPlan.model_validate(data), _cast())
    assert result.status == QCStatus.WARN
    assert any("no reveal/promise/character-arc progress" in r for r in result.reasons)


def test_unknown_mystery_reference_blocks() -> None:
    data = copy.deepcopy(fx.season_plan())
    data["reveals"][0]["mystery_id"] = "MYS_UNKNOWN"
    result = SeasonValidator().validate(SeasonPlan.model_validate(data), _cast())
    assert result.status == QCStatus.BLOCK
    assert any("unknown mystery" in r for r in result.reasons)
