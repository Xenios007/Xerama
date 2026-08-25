import json
import logging

from xerama.domain.enums import JobStage
from xerama.observability.logging import (
    CorrelationIdFilter,
    JsonLogFormatter,
    get_correlation_id,
    new_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyCostRecordRepository,
    SQLAlchemyJobRepository,
    SQLAlchemyProjectRepository,
)
from xerama.services.cost_service import CostRecordService
from xerama.services.observability_service import ObservabilityService


# --- structured logging / correlation id -----------------------------------


def test_correlation_id_defaults_to_placeholder() -> None:
    assert get_correlation_id() == "-"


def test_set_and_reset_correlation_id() -> None:
    token = set_correlation_id("abc123")
    try:
        assert get_correlation_id() == "abc123"
    finally:
        reset_correlation_id(token)
    assert get_correlation_id() == "-"


def test_new_correlation_id_is_unique() -> None:
    assert new_correlation_id() != new_correlation_id()


def test_correlation_id_filter_injects_current_id() -> None:
    token = set_correlation_id("req-1")
    try:
        record = logging.LogRecord("x", logging.INFO, __file__, 1, "hello", None, None)
        assert CorrelationIdFilter().filter(record) is True
        assert record.correlation_id == "req-1"
    finally:
        reset_correlation_id(token)


def test_json_log_formatter_produces_structured_json_with_correlation_id() -> None:
    token = set_correlation_id("req-2")
    try:
        record = logging.LogRecord("xerama.test", logging.WARNING, __file__, 1, "something happened", None, None)
        CorrelationIdFilter().filter(record)
        formatted = JsonLogFormatter().format(record)
    finally:
        reset_correlation_id(token)

    payload = json.loads(formatted)
    assert payload["correlation_id"] == "req-2"
    assert payload["level"] == "WARNING"
    assert payload["logger"] == "xerama.test"
    assert payload["message"] == "something happened"


def test_json_log_formatter_never_leaks_prompt_text() -> None:
    """Structured fields only - no field for prompt/payload content."""
    record = logging.LogRecord(
        "xerama.ai_gateway", logging.WARNING, __file__, 1,
        "provider error role=judge model=x kind=timeout attempt=1", None, None,
    )
    CorrelationIdFilter().filter(record)
    payload = json.loads(JsonLogFormatter().format(record))
    assert "prompt" not in payload
    assert "system_prompt" not in payload
    assert "user_prompt" not in payload


# --- observability service --------------------------------------------------


async def test_queue_depth_counts_queued_jobs(session) -> None:
    project = await SQLAlchemyProjectRepository(session).create("p")
    job_repo = SQLAlchemyJobRepository(session)
    await job_repo.enqueue(project.id, JobStage.CONCEPT_GENERATION, payload={})
    await job_repo.enqueue(project.id, JobStage.JUDGE, payload={})
    await session.commit()

    service = ObservabilityService(
        job_repo=job_repo, cost_service=CostRecordService(repo=SQLAlchemyCostRecordRepository(session))
    )
    assert await service.queue_depth() == 2


async def test_stage_durations_averages_finished_jobs(session) -> None:
    project = await SQLAlchemyProjectRepository(session).create("p")
    job_repo = SQLAlchemyJobRepository(session)
    job1 = await job_repo.create(project.id, JobStage.CONCEPT_GENERATION)
    await job_repo.start(job1.id)
    await job_repo.succeed(job1.id)
    job2 = await job_repo.create(project.id, JobStage.CONCEPT_GENERATION)
    await job_repo.start(job2.id)
    await job_repo.succeed(job2.id)
    # A still-running job (no finished_at) must not skew or crash the average.
    job3 = await job_repo.create(project.id, JobStage.JUDGE)
    await job_repo.start(job3.id)
    await session.commit()

    service = ObservabilityService(
        job_repo=job_repo, cost_service=CostRecordService(repo=SQLAlchemyCostRecordRepository(session))
    )
    durations = await service.stage_durations(project.id)
    by_stage = {d.stage: d for d in durations}
    assert by_stage["concept_generation"].sample_count == 2
    assert by_stage["concept_generation"].average_seconds >= 0.0
    assert "judge" not in by_stage  # no finished_at yet


async def test_provider_reliability_counts_failures_and_retries(session) -> None:
    project = await SQLAlchemyProjectRepository(session).create("p")
    cost_repo = SQLAlchemyCostRecordRepository(session)
    await cost_repo.create(provider="flaky", model="m", stage="image_generation", project_id=project.id, attempt=1)
    await cost_repo.create(
        provider="flaky", model="m", stage="image_generation", project_id=project.id,
        attempt=2, failure_reason="timeout",
    )
    await cost_repo.create(provider="reliable", model="m", stage="image_generation", project_id=project.id, attempt=1)
    await session.commit()

    service = ObservabilityService(
        job_repo=SQLAlchemyJobRepository(session), cost_service=CostRecordService(repo=cost_repo)
    )
    reliability = await service.provider_reliability(project.id)
    by_provider = {r.provider: r for r in reliability}
    assert by_provider["flaky"].attempt_count == 2
    assert by_provider["flaky"].failure_count == 1
    assert by_provider["flaky"].retry_count == 1
    assert by_provider["reliable"].attempt_count == 1
    assert by_provider["reliable"].failure_count == 0
