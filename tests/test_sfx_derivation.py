from xerama.domain.scene import MicroBeat, Shot
from xerama.pipeline.sfx_derivation import MAX_SFX_CANDIDATES_PER_SHOT, derive_sfx_candidates


def _shot(**overrides) -> Shot:
    base = dict(shot_number=1, scene_number=1, duration_seconds=5.0)
    base.update(overrides)
    return Shot(**base)


def test_no_candidates_when_no_keywords_match() -> None:
    shot = _shot(action="Mara looks up thoughtfully.")
    assert derive_sfx_candidates(shot) == []


def test_matches_keyword_in_action_text_with_default_window() -> None:
    shot = _shot(action="The door slams shut behind her.", duration_seconds=4.0)
    candidates = derive_sfx_candidates(shot)
    assert candidates == [("door slams", 0.0, 1.0)]


def test_prefers_micro_beat_timing_over_action_fallback() -> None:
    shot = _shot(
        action="a door somewhere",
        micro_beats=[
            MicroBeat(start_seconds=2.0, end_seconds=2.5, description="the door slams shut"),
        ],
    )
    candidates = derive_sfx_candidates(shot)
    assert candidates == [("door slams", 2.0, 2.5)]


def test_caps_at_max_candidates_per_shot() -> None:
    shot = _shot(action="a door slams, glass breaks, a phone rings, a car engine roars")
    candidates = derive_sfx_candidates(shot)
    assert len(candidates) == MAX_SFX_CANDIDATES_PER_SHOT


def test_does_not_duplicate_same_description_twice() -> None:
    shot = _shot(
        action="a gun fires",
        micro_beats=[MicroBeat(start_seconds=0.0, end_seconds=1.0, description="a gunshot rings out")],
    )
    candidates = derive_sfx_candidates(shot)
    descriptions = [c[0] for c in candidates]
    assert descriptions.count("gunshot") == 1
