"""Deterministic render-staleness detection (MODULE-047).

"Define dirty/stale propagation when upstream assets change" - implemented
as a pure, on-demand check rather than an eager write-time hook scattered
across every place a shot's approved take/script could change: a render
is stale if the episode's script version has moved on, or if any asset id
it actually consumed is no longer the episode's current approved asset for
that role. This needs no new state to keep in sync and can never drift out
of date the way a push-based flag could.
"""

from xerama.domain.episode_render import EpisodeRender


def check_staleness(
    render: EpisodeRender, current_script_version: int, current_input_asset_ids: set[str]
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if render.source_script_version != current_script_version:
        reasons.append(
            f"episode script version changed ({render.source_script_version} -> "
            f"{current_script_version}) since this render"
        )
    missing_or_changed = set(render.input_asset_ids) - current_input_asset_ids
    if missing_or_changed:
        reasons.append(
            f"{len(missing_or_changed)} asset(s) this render used are no longer the current "
            "approved production asset for their shot/cue"
        )
    return bool(reasons), reasons
