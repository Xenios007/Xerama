"""Aggregate media eval runs by (shot_class, provider) (MODULE-073,
ADR-024's "cost per accepted output" applied to a deliberate benchmark
instead of passive production telemetry - see `pipeline/cost_aggregation.py`
for the production-telemetry version this mirrors).

Grouping key is always `(shot_class, provider)`, never collapsed across
shot classes - "benchmark ... by shot class," never one global winner
(the same non-negotiable MODULE-064/072 already established for
provider/model comparisons).
"""

from collections import defaultdict

from pydantic import BaseModel

from xerama.domain.enums import ShotClass
from xerama.domain.media_eval import MediaEvalRunResult


class ShotClassProviderBenchmark(BaseModel):
    shot_class: ShotClass
    provider: str
    dataset_version: str
    sample_count: int
    generation_success_rate: float
    acceptance_rate: float
    avg_attempts: float | None = None
    avg_latency_ms: float | None = None
    # Numerator sums every attempt's estimated cost (so a provider that
    # needed retries costs more per accepted unit); denominator counts
    # only accepted outputs - ADR-024's ratio, over `estimated_cost_usd`
    # rather than real billing telemetry (see that field's docstring in
    # domain/media_eval.py for why).
    estimated_cost_per_accepted_usd: float | None = None


def _average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def summarize_by_shot_class(results: list[MediaEvalRunResult]) -> list[ShotClassProviderBenchmark]:
    groups: dict[tuple[ShotClass, str, str], list[MediaEvalRunResult]] = defaultdict(list)
    for result in results:
        if not result.provider:
            continue  # generation failed before any provider was selected - nothing to attribute
        groups[(result.shot_class, result.provider, result.dataset_version)].append(result)

    benchmarks = []
    for (shot_class, provider, dataset_version), group in groups.items():
        succeeded = [r for r in group if r.generation_succeeded]
        accepted = [r for r in group if r.accepted]
        attempts = [float(r.attempts) for r in group if r.attempts]
        latencies = [r.latency_ms for r in group if r.latency_ms is not None]

        total_estimated_cost = sum(
            r.estimated_cost_usd for r in group if r.estimated_cost_usd is not None
        )
        cost_per_accepted = (total_estimated_cost / len(accepted)) if accepted else None

        benchmarks.append(
            ShotClassProviderBenchmark(
                shot_class=shot_class,
                provider=provider,
                dataset_version=dataset_version,
                sample_count=len(group),
                generation_success_rate=round(len(succeeded) / len(group), 4),
                acceptance_rate=round(len(accepted) / len(group), 4),
                avg_attempts=_average(attempts),
                avg_latency_ms=_average(latencies),
                estimated_cost_per_accepted_usd=(
                    round(cost_per_accepted, 4) if cost_per_accepted is not None else None
                ),
            )
        )
    benchmarks.sort(key=lambda b: (b.shot_class.value, b.provider))
    return benchmarks
