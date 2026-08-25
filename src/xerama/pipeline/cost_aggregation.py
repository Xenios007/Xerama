"""Deterministic cost aggregation (MODULE-049, ADR-024).

"Xerama evaluates models/providers using cost per accepted image, accepted
video second and accepted episode, incorporating retries and rejection
rates" - the numerator sums every attempt's known cost (so a provider
that needed three retries to get one accepted output costs more per
accepted unit than one that succeeded on the first try), while the
denominator counts only what was actually accepted. No LLM call - pure
arithmetic over already-persisted `CostRecord`s.
"""

from pydantic import BaseModel

from xerama.domain.cost import CostRecord


class AcceptedOutputCost(BaseModel):
    unit: str
    total_known_cost_usd: float
    unknown_cost_attempts: int
    accepted_quantity: float
    cost_per_accepted_unit_usd: float | None = None


def summarize_cost_per_accepted(
    records: list[CostRecord], unit: str, accepted_asset_ids: set[str]
) -> AcceptedOutputCost:
    """`accepted_quantity` is a count for `unit="images"` (one accepted
    image = 1) but a sum of `quantity` for e.g. `unit="seconds"` (so
    "cost per accepted video second" is genuinely per-second, not
    per-clip)."""
    relevant = [r for r in records if r.unit == unit]
    total_known_cost = sum(r.cost_usd for r in relevant if r.cost_known and r.cost_usd is not None)
    unknown_count = sum(1 for r in relevant if not r.cost_known)

    accepted = [r for r in relevant if r.asset_id is not None and r.asset_id in accepted_asset_ids]
    accepted_quantity = float(len(accepted)) if unit == "images" else sum(r.quantity for r in accepted)

    cost_per_unit = (total_known_cost / accepted_quantity) if accepted_quantity > 0 else None
    return AcceptedOutputCost(
        unit=unit,
        total_known_cost_usd=total_known_cost,
        unknown_cost_attempts=unknown_count,
        accepted_quantity=accepted_quantity,
        cost_per_accepted_unit_usd=cost_per_unit,
    )


def cost_per_episode(records: list[CostRecord]) -> dict[str, float]:
    """Total known cost grouped by `episode_id` - every stage's cost
    (story/image/video/audio/assembly) rolls up under whichever episode
    it was attributed to. Records with no `episode_id` or unknown cost
    are excluded from the total (not silently treated as zero)."""
    totals: dict[str, float] = {}
    for record in records:
        if record.episode_id and record.cost_known and record.cost_usd is not None:
            totals[record.episode_id] = totals.get(record.episode_id, 0.0) + record.cost_usd
    return totals
