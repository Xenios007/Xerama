from xerama.domain.enums import CanonChangeType
from xerama.pipeline.canon_commit import build_canon_events, classify_change_type


def test_classify_change_type_secret_exposed() -> None:
    assert classify_change_type("Lena's secret is exposed to Mara") == CanonChangeType.SECRET_EXPOSED


def test_classify_change_type_injury() -> None:
    assert classify_change_type("Mara is injured in the car crash") == CanonChangeType.INJURY_ADDED


def test_classify_change_type_location_move() -> None:
    assert classify_change_type("Mara arrives at the old cabin") == CanonChangeType.CHARACTER_MOVES_LOCATION


def test_classify_change_type_prop_ownership() -> None:
    assert classify_change_type("Mara steals the ring") == CanonChangeType.PROP_OWNERSHIP_CHANGE


def test_classify_change_type_relationship() -> None:
    assert classify_change_type("Mara no longer trusts Lena") == CanonChangeType.RELATIONSHIP_CHANGE


def test_classify_change_type_defaults_to_learns_fact() -> None:
    assert classify_change_type("something ambiguous happens") == CanonChangeType.CHARACTER_LEARNS_FACT


def test_build_canon_events_preserves_description_and_episode_number() -> None:
    events = build_canon_events(3, ["Mara steals the ring", "Lena's secret is exposed"])
    assert len(events) == 2
    assert events[0].episode_number == 3
    assert events[0].description == "Mara steals the ring"
    assert events[0].change_type == CanonChangeType.PROP_OWNERSHIP_CHANGE
    assert events[0].committed is True
    assert events[1].change_type == CanonChangeType.SECRET_EXPOSED


def test_build_canon_events_empty_list() -> None:
    assert build_canon_events(1, []) == []
