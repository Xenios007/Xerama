"""Bounded canon-context builder (Module 02).

Builds the compact `CanonSnapshot` handed to episode generation from
structured canon (committed `CanonEvent` rows + prior episode outlines) -
never from raw prior scripts/chat history. The `recap` field is convenience
context for the model, not the source of truth - the structured fields
(`locked_facts`, `character_summaries`, `unresolved_hooks`, `prior_events`)
are what continuity actually rests on. See
docs/ARCHITECTURE.md "Canonical state over prompt memory" and
modules/02_MULTI_EPISODE_ENGINE.md.
"""

from xerama.domain.canon import CanonEvent, CanonSnapshot
from xerama.domain.character import CharacterCast
from xerama.domain.story import SeriesBible
from xerama.repositories.interfaces import EpisodeRecord


def build_canon_snapshot(
    bible: SeriesBible,
    cast: CharacterCast,
    prior_committed_episodes: list[EpisodeRecord],
    committed_events: list[CanonEvent],
) -> CanonSnapshot:
    character_summaries = [
        f"{c.name} ({c.role}): goal={c.goal or 'unknown'}, secret={c.secret or 'none known'}"
        for c in cast.characters
    ]
    prior_events = [event.description for event in committed_events]

    unresolved_hooks: list[str] = []
    if prior_committed_episodes:
        last = max(prior_committed_episodes, key=lambda e: e.episode_number)
        if last.outline.cliffhanger.event:
            unresolved_hooks.append(
                f"Episode {last.episode_number} ended on: {last.outline.cliffhanger.event}"
            )

    ordered = sorted(prior_committed_episodes, key=lambda e: e.episode_number)
    recap = " ".join(
        f"Ep{ep.episode_number}: {ep.outline.objective} Ends: {ep.outline.cliffhanger.event}."
        for ep in ordered
    )

    return CanonSnapshot(
        series_title=bible.title,
        locked_facts=bible.locked_facts,
        character_summaries=character_summaries,
        unresolved_hooks=unresolved_hooks,
        prior_events=prior_events,
        recap=recap,
    )
