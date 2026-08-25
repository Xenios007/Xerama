"""AI evaluation harness (MODULE-072).

Runs a versioned `EvalCase` (eval/datasets.py) through the *real*
`AIGateway` - "live eval opt-in": this harness never runs on its own; a
caller (an explicit API call or test with a `FakeLLMProvider`) decides
when. Nothing here duplicates `AIGateway`'s own retry/schema-validation
logic - a case either succeeds (schema-valid, possibly after
`AIGateway`'s internal retries) or raises `XeramaGenerationError` after
exhausting them, exactly as any other pipeline stage using this role
would experience it. That "did it succeed within the gateway's normal
retry budget" *is* the schema-success signal for benchmarking purposes,
not a separate one-shot-only measurement.
"""

import time

from xerama.eval.datasets import EvalCase
from xerama.pipeline.ai_gateway import AIGateway, XeramaGenerationError
from xerama.pipeline.eval_quality import score_concept_candidate, score_episode_script, score_judge_result
from xerama.domain.episode import EpisodeScript
from xerama.domain.eval import EvalRunResult
from xerama.domain.story import ConceptCandidate, JudgeResult

_SCORERS = {
    ConceptCandidate: score_concept_candidate,
    JudgeResult: score_judge_result,
    EpisodeScript: score_episode_script,
}


class EvalHarness:
    """`run_case` returns an `EvalRunResult` with `id=""` - a transient,
    not-yet-persisted value (this is pure computation, no repository
    involved). `EvalService.run_dataset` forwards its fields to
    `EvalRunRepository.create(...)`, which returns the real, ID-assigned
    persisted record - the same "service forwards fields, repository
    owns identity" split every other service in this codebase already
    follows (e.g. `AnalyticsIngestionService.import_metrics`)."""

    def __init__(self, gateway: AIGateway, provider_name: str) -> None:
        self._gateway = gateway
        self._provider_name = provider_name

    async def run_case(self, case: EvalCase, dataset_version: str) -> EvalRunResult:
        model = self._gateway.resolve_model(case.role)
        started = time.perf_counter()
        try:
            result = await self._gateway.generate(
                role=case.role,
                schema=case.schema,
                system_prompt=case.system_prompt,
                user_prompt=case.user_prompt,
            )
        except XeramaGenerationError as exc:
            return EvalRunResult(
                id="",
                case_id=case.id,
                role=case.role,
                dataset_version=dataset_version,
                provider=self._provider_name,
                model=model,
                schema_valid=False,
                latency_ms=(time.perf_counter() - started) * 1000,
                error=str(exc),
            )

        latency_ms = (time.perf_counter() - started) * 1000
        scorer = _SCORERS.get(case.schema)
        quality_score, quality_reasons = scorer(result, case) if scorer else (None, [])
        return EvalRunResult(
            id="",
            case_id=case.id,
            role=case.role,
            dataset_version=dataset_version,
            provider=self._provider_name,
            model=model,
            schema_valid=True,
            quality_score=quality_score,
            quality_reasons=quality_reasons,
            latency_ms=latency_ms,
            raw_response_excerpt=result.model_dump_json()[:500],
        )
