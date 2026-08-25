"""Media evaluation service (MODULE-073) - wires the harness, dataset,
and repository together. `run_dataset` is the only way a benchmark run
happens - never triggered automatically ("live eval opt-in")."""

from xerama.domain.asset import AssetType
from xerama.domain.media_eval import MediaEvalRunResult
from xerama.eval.media_datasets import DATASET_VERSION, cases_for_asset_type
from xerama.pipeline.media_eval_aggregation import ShotClassProviderBenchmark, summarize_by_shot_class
from xerama.pipeline.media_eval_harness import MediaEvalHarness
from xerama.repositories.interfaces import MediaEvalRunRepository


class MediaEvalService:
    def __init__(self, harness: MediaEvalHarness, repo: MediaEvalRunRepository) -> None:
        self._harness = harness
        self._repo = repo

    async def run_dataset(self, asset_type: AssetType) -> list[MediaEvalRunResult]:
        results = []
        for case in cases_for_asset_type(asset_type):
            outcome = await self._harness.run_case(case, DATASET_VERSION)
            persisted = await self._repo.create(
                case_id=outcome.case_id,
                shot_class=outcome.shot_class.value,
                asset_type=outcome.asset_type.value,
                dataset_version=outcome.dataset_version,
                provider=outcome.provider,
                generation_succeeded=outcome.generation_succeeded,
                attempts=outcome.attempts,
                latency_ms=outcome.latency_ms,
                estimated_cost_usd=outcome.estimated_cost_usd,
                qc_results=[r.model_dump() for r in outcome.qc_results],
                accepted=outcome.accepted,
                asset_id=outcome.asset_id,
                error=outcome.error,
            )
            results.append(persisted)
        return results

    async def benchmark_by_shot_class(self) -> list[ShotClassProviderBenchmark]:
        results = await self._repo.list_all()
        return summarize_by_shot_class(results)

    async def record_human_preference(self, run_id: str, preference: str) -> MediaEvalRunResult:
        return await self._repo.set_human_preference(run_id, preference)
