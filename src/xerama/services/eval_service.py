"""AI evaluation service (MODULE-072) - wires the harness, dataset, and
repository together. `run_dataset` is the only way a benchmark run
happens - never triggered automatically, always an explicit call
("live eval opt-in")."""

from xerama.domain.enums import ModelRole
from xerama.domain.eval import EvalRunResult
from xerama.eval.datasets import DATASET_VERSION, cases_for_role
from xerama.pipeline.eval_aggregation import ModelRoleBenchmark, summarize_by_role
from xerama.pipeline.eval_harness import EvalHarness
from xerama.repositories.interfaces import EvalRunRepository


class EvalService:
    def __init__(self, harness: EvalHarness, repo: EvalRunRepository) -> None:
        self._harness = harness
        self._repo = repo

    async def run_dataset(self, role: ModelRole) -> list[EvalRunResult]:
        """Runs every case for `role` and persists each result. Returns
        an empty list (not an error) for a role with no dataset yet -
        e.g. `CONTINUITY_CHECKER`, which has no LLM call to benchmark at
        all (see `eval/datasets.py`)."""
        results = []
        for case in cases_for_role(role):
            outcome = await self._harness.run_case(case, DATASET_VERSION)
            persisted = await self._repo.create(
                case_id=outcome.case_id,
                role=outcome.role.value,
                dataset_version=outcome.dataset_version,
                provider=outcome.provider,
                model=outcome.model,
                schema_valid=outcome.schema_valid,
                quality_score=outcome.quality_score,
                quality_reasons=outcome.quality_reasons,
                latency_ms=outcome.latency_ms,
                error=outcome.error,
                raw_response_excerpt=outcome.raw_response_excerpt,
            )
            results.append(persisted)
        return results

    async def benchmark_for_role(self, role: ModelRole) -> list[ModelRoleBenchmark]:
        results = await self._repo.list_by_role(role.value)
        return summarize_by_role(results)

    async def record_human_preference(self, run_id: str, preference: str) -> EvalRunResult:
        return await self._repo.set_human_preference(run_id, preference)
