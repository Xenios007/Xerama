"""Canon commit - turns an episode outline's free-text `canon_changes` into
typed, persisted `CanonEvent` records.

See docs/DATA_MODEL.md "Canon Commit Rule" and ADR-006 (generated output is
not canon until validated). `classify_change_type` is a deliberately simple
keyword heuristic, not a model call - see
docs/IMPLEMENTATION_STATUS.md "Documented deviations" for why this stayed a
heuristic rather than an LLM classification call, and
research/CODING_READINESS_CHECKLIST.md's "initial heuristics" guidance.
Nothing downstream branches on `change_type` correctness yet, so a
mis-classified event is a soft quality issue, not a correctness bug - the
free-text `description` is always preserved regardless of classification.
"""

from xerama.domain.canon import CanonEvent
from xerama.domain.enums import CanonChangeType

_KEYWORD_RULES: list[tuple[tuple[str, ...], CanonChangeType]] = [
    (("exposed", "revealed to everyone", "made public"), CanonChangeType.SECRET_EXPOSED),
    (("injur", "wound", "hurt", "hospital"), CanonChangeType.INJURY_ADDED),
    (("heals", "recovers", "no longer injured"), CanonChangeType.INJURY_REMOVED),
    (("moves to", "arrives at", "travels to", "relocat"), CanonChangeType.CHARACTER_MOVES_LOCATION),
    (("steals", "gives", "hands over", "takes possession", "ownership"), CanonChangeType.PROP_OWNERSHIP_CHANGE),
    (("promises", "vows", "swears"), CanonChangeType.PROMISE_CREATED),
    (("pays off", "fulfills", "keeps her promise", "keeps his promise"), CanonChangeType.PROMISE_PAID_OFF),
    (
        ("relationship", "trust", "no longer trusts", "falls for", "breaks up"),
        CanonChangeType.RELATIONSHIP_CHANGE,
    ),
]


def classify_change_type(description: str) -> CanonChangeType:
    lowered = description.lower()
    for keywords, change_type in _KEYWORD_RULES:
        if any(keyword in lowered for keyword in keywords):
            return change_type
    # Default bucket: most canon_changes are some character learning
    # something new, which is also the safest generic fallback.
    return CanonChangeType.CHARACTER_LEARNS_FACT


def build_canon_events(episode_number: int, canon_changes: list[str]) -> list[CanonEvent]:
    return [
        CanonEvent(
            change_type=classify_change_type(change),
            episode_number=episode_number,
            description=change,
            committed=True,
        )
        for change in canon_changes
    ]
