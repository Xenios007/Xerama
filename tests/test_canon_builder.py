import fixtures as fx
from xerama.domain.canon import CanonEvent
from xerama.domain.character import CharacterCast
from xerama.domain.enums import CanonChangeType
from xerama.domain.episode import Cliffhanger, EpisodeOutline
from xerama.domain.story import SeriesBible
from xerama.pipeline.canon_builder import build_canon_snapshot
from xerama.repositories.interfaces import EpisodeRecord


def _bible() -> SeriesBible:
    return SeriesBible.model_validate(fx.bible())


def _cast() -> CharacterCast:
    return CharacterCast.model_validate(fx.cast())


def _episode_record(number: int, cliffhanger_event: str) -> EpisodeRecord:
    outline = EpisodeOutline.model_validate(fx.outline(number))
    outline.cliffhanger = Cliffhanger(type=outline.cliffhanger.type, event=cliffhanger_event)
    return EpisodeRecord(
        id=f"ep-{number}", series_id="series-1", episode_number=number, status="canon_committed", outline=outline
    )


def test_empty_history_produces_bounded_defaults() -> None:
    snapshot = build_canon_snapshot(_bible(), _cast(), [], [])
    assert snapshot.series_title == "Blood Sisters"
    assert snapshot.locked_facts == _bible().locked_facts
    assert snapshot.unresolved_hooks == []
    assert snapshot.prior_events == []
    assert len(snapshot.character_summaries) == 2


def test_unresolved_hook_uses_latest_committed_episode() -> None:
    episodes = [_episode_record(1, "the first mask comes off"), _episode_record(2, "the second reveal")]
    snapshot = build_canon_snapshot(_bible(), _cast(), episodes, [])
    assert snapshot.unresolved_hooks == ["Episode 2 ended on: the second reveal"]


def test_prior_events_come_from_committed_canon_events_only() -> None:
    events = [
        CanonEvent(
            change_type=CanonChangeType.SECRET_EXPOSED,
            episode_number=1,
            description="Lena's secret is exposed",
            committed=True,
        )
    ]
    snapshot = build_canon_snapshot(_bible(), _cast(), [], events)
    assert snapshot.prior_events == ["Lena's secret is exposed"]


def test_recap_is_ordered_by_episode_number() -> None:
    episodes = [_episode_record(2, "second hook"), _episode_record(1, "first hook")]
    snapshot = build_canon_snapshot(_bible(), _cast(), episodes, [])
    assert snapshot.recap.index("Ep1:") < snapshot.recap.index("Ep2:")
