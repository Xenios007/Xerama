"""Provider ranking / optimization recommendations (MODULE-064).

Extends MODULE-049's cost ledger and MODULE-044's QC ledger into a
ranked, explainable comparison - "explain evidence behind
recommendations" is satisfied by returning every component alongside the
composite score, never just a bare number. Never writes anything -
purely advisory, matching "suggest... separately from automatic canon
changes."
"""

from collections import defaultdict

from pydantic import BaseModel

from xerama.domain.cost import CostRecord

Objective = str  # "quality" | "budget" | "speed" | "balanced"

_OBJECTIVE_WEIGHTS: dict[str, dict[str, float]] = {
    "quality": {"qc": 0.6, "accept": 0.3, "cost": 0.05, "latency": 0.05},
    "budget": {"qc": 0.1, "accept": 0.2, "cost": 0.6, "latency": 0.1},
    "speed": {"qc": 0.1, "accept": 0.2, "cost": 0.1, "latency": 0.6},
    "balanced": {"qc": 0.25, "accept": 0.25, "cost": 0.25, "latency": 0.25},
}


class ProviderRanking(BaseModel):
    provider: str
    stage: str
    sample_count: int
    accepted_rate: float | None = None
    avg_cost_usd: float | None = None
    avg_latency_ms: float | None = None
    avg_qc_score: float | None = None
    composite_score: float
    objective: str


def rank_providers(
    cost_records: list[CostRecord],
    accepted_asset_ids: set[str],
    qc_scores_by_asset: dict[str, float],
    objective: Objective = "balanced",
) -> list[ProviderRanking]:
    weights = _OBJECTIVE_WEIGHTS.get(objective, _OBJECTIVE_WEIGHTS["balanced"])
    by_key: dict[tuple[str, str], list[CostRecord]] = defaultdict(list)
    for record in cost_records:
        if not record.provider:
            continue
        by_key[(record.provider, record.stage)].append(record)

    rankings: list[ProviderRanking] = []
    for (provider, stage), records in by_key.items():
        with_asset = [r for r in records if r.asset_id]
        accepted = [r for r in with_asset if r.asset_id in accepted_asset_ids]
        accepted_rate = (len(accepted) / len(with_asset)) if with_asset else None

        known_costs = [r.cost_usd for r in records if r.cost_known and r.cost_usd is not None]
        avg_cost = sum(known_costs) / len(known_costs) if known_costs else None

        latencies = [r.latency_ms for r in records if r.latency_ms is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else None

        qc_scores = [qc_scores_by_asset[r.asset_id] for r in with_asset if r.asset_id in qc_scores_by_asset]
        avg_qc = sum(qc_scores) / len(qc_scores) if qc_scores else None

        # Normalize each component to 0-1 ("higher is better"); an unknown
        # component contributes 0 rather than a fabricated neutral value -
        # its `None` field in the result makes that visible, not hidden.
        quality_component = (avg_qc / 10.0) if avg_qc is not None else 0.0
        accept_component = accepted_rate if accepted_rate is not None else 0.0
        cost_component = (1.0 / (1.0 + avg_cost)) if avg_cost is not None else 0.0
        latency_component = (1.0 / (1.0 + avg_latency / 1000.0)) if avg_latency is not None else 0.0

        composite = (
            weights["qc"] * quality_component
            + weights["accept"] * accept_component
            + weights["cost"] * cost_component
            + weights["latency"] * latency_component
        )
        rankings.append(
            ProviderRanking(
                provider=provider,
                stage=stage,
                sample_count=len(records),
                accepted_rate=accepted_rate,
                avg_cost_usd=avg_cost,
                avg_latency_ms=avg_latency,
                avg_qc_score=avg_qc,
                composite_score=round(composite, 4),
                objective=objective,
            )
        )
    return sorted(rankings, key=lambda r: r.composite_score, reverse=True)
