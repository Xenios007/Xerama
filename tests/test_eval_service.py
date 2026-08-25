import json

import fixtures as fx
from xerama.config import ModelRoleRegistry, Settings
from xerama.domain.enums import ModelRole
from xerama.eval.datasets import DATASET_VERSION, cases_for_role
from xerama.pipeline.ai_gateway import AIGateway
from xerama.pipeline.eval_harness import EvalHarness
from xerama.providers.errors import ProviderError, ProviderErrorKind
from xerama.providers.fake import FakeLLMProvider
from xerama.providers.health import ProviderHealthTracker
from xerama.repositories.sqlalchemy_impl import SQLAlchemyEvalRunRepository
from xerama.services.eval_service import EvalService


def _gateway(responses: list) -> AIGateway:
    provider = FakeLLMProvider(responses)
    return AIGateway(provider=provider, roles=ModelRoleRegistry(Settings()), health=ProviderHealthTracker())


# --- harness (MODULE-072) - deterministic, FakeLLMProvider only ------------


async def test_harness_run_case_scores_a_successful_judge_response() -> None:
    gateway = _gateway([json.dumps(fx.judge_result("A"))])
    harness = EvalHarness(gateway=gateway, provider_name="fake")
    case = cases_for_role(ModelRole.JUDGE)[0]

    outcome = await harness.run_case(case, DATASET_VERSION)

    assert outcome.schema_valid is True
    assert outcome.quality_score == 10.0
    assert outcome.case_id == case.id
    assert outcome.dataset_version == DATASET_VERSION
    assert outcome.provider == "fake"
    assert outcome.latency_ms is not None and outcome.latency_ms >= 0


async def test_harness_run_case_records_a_non_retriable_provider_failure() -> None:
    gateway = _gateway([ProviderError(ProviderErrorKind.AUTHENTICATION, "bad key")])
    harness = EvalHarness(gateway=gateway, provider_name="fake")
    case = cases_for_role(ModelRole.JUDGE)[0]

    outcome = await harness.run_case(case, DATASET_VERSION)

    assert outcome.schema_valid is False
    assert outcome.quality_score is None
    assert "bad key" in outcome.error


async def test_harness_run_case_uses_the_configured_model_for_the_role() -> None:
    gateway = _gateway([json.dumps(fx.judge_result("A"))])
    harness = EvalHarness(gateway=gateway, provider_name="fake")
    case = cases_for_role(ModelRole.JUDGE)[0]

    outcome = await harness.run_case(case, DATASET_VERSION)

    assert outcome.model == gateway.resolve_model(ModelRole.JUDGE)


# --- service + repository (real DB via the `session` fixture) --------------


async def test_run_dataset_persists_one_result_per_case(session) -> None:
    cases = cases_for_role(ModelRole.JUDGE)
    responses = [json.dumps(fx.judge_result("A")) for _ in cases]
    gateway = _gateway(responses)
    harness = EvalHarness(gateway=gateway, provider_name="fake")
    service = EvalService(harness=harness, repo=SQLAlchemyEvalRunRepository(session))

    results = await service.run_dataset(ModelRole.JUDGE)
    await session.commit()

    assert len(results) == len(cases)
    assert all(r.id for r in results)  # real, repo-assigned ids - not the harness placeholder
    assert all(r.schema_valid for r in results)


async def test_run_dataset_returns_empty_for_a_role_with_no_dataset(session) -> None:
    gateway = _gateway([])
    harness = EvalHarness(gateway=gateway, provider_name="fake")
    service = EvalService(harness=harness, repo=SQLAlchemyEvalRunRepository(session))

    results = await service.run_dataset(ModelRole.CONTINUITY_CHECKER)
    assert results == []


async def test_benchmark_for_role_aggregates_persisted_runs(session) -> None:
    cases = cases_for_role(ModelRole.JUDGE)
    responses = [json.dumps(fx.judge_result("A")) for _ in cases]
    gateway = _gateway(responses)
    harness = EvalHarness(gateway=gateway, provider_name="fake")
    service = EvalService(harness=harness, repo=SQLAlchemyEvalRunRepository(session))

    await service.run_dataset(ModelRole.JUDGE)
    await session.commit()

    benchmarks = await service.benchmark_for_role(ModelRole.JUDGE)
    assert len(benchmarks) == 1
    assert benchmarks[0].sample_count == len(cases)
    assert benchmarks[0].schema_success_rate == 1.0


async def test_record_human_preference_updates_the_persisted_run(session) -> None:
    responses = [json.dumps(fx.judge_result("A")) for _ in cases_for_role(ModelRole.JUDGE)]
    gateway = _gateway(responses)
    harness = EvalHarness(gateway=gateway, provider_name="fake")
    repo = SQLAlchemyEvalRunRepository(session)
    service = EvalService(harness=harness, repo=repo)

    results = await service.run_dataset(ModelRole.JUDGE)
    await session.commit()

    updated = await service.record_human_preference(results[0].id, "preferred")
    await session.commit()

    assert updated.human_preference == "preferred"
