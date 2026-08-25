"""Aggregate eval runs by (role, provider, model) (MODULE-072).

"Compare models by logical role, not one global winner" - grouping key
is always `(role, provider, model)`, never collapsed across roles: a
model that's excellent at `JUDGE` and mediocre at `EPISODE_WRITER`
should never average into one misleading number.
"""

from collections import defaultdict

from pydantic import BaseModel

from xerama.domain.enums import ModelRole
from xerama.domain.eval import EvalRunResult


class ModelRoleBenchmark(BaseModel):
    role: ModelRole
    provider: str
    model: str
    dataset_version: str
    sample_count: int
    schema_success_rate: float
    # None only when every sample in the group is schema-invalid (no
    # quality score exists to average) - never fabricated as 0.
    avg_quality_score: float | None = None
    avg_latency_ms: float | None = None


def _average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def summarize_by_role(results: list[EvalRunResult]) -> list[ModelRoleBenchmark]:
    groups: dict[tuple[ModelRole, str, str, str], list[EvalRunResult]] = defaultdict(list)
    for result in results:
        groups[(result.role, result.provider, result.model, result.dataset_version)].append(result)

    benchmarks = []
    for (role, provider, model, dataset_version), group in groups.items():
        schema_valid_count = sum(1 for r in group if r.schema_valid)
        quality_scores = [r.quality_score for r in group if r.quality_score is not None]
        latencies = [r.latency_ms for r in group if r.latency_ms is not None]
        benchmarks.append(
            ModelRoleBenchmark(
                role=role,
                provider=provider,
                model=model,
                dataset_version=dataset_version,
                sample_count=len(group),
                schema_success_rate=round(schema_valid_count / len(group), 4),
                avg_quality_score=_average(quality_scores),
                avg_latency_ms=_average(latencies),
            )
        )
    benchmarks.sort(key=lambda b: (b.role.value, b.provider, b.model))
    return benchmarks
