import asyncio

import pytest

from xerama.domain.enums import JobStage, JobStatus, ProviderErrorKind
from xerama.providers.errors import ProviderError
from xerama.repositories.sqlalchemy_impl import SQLAlchemyJobRepository, SQLAlchemyProjectRepository
from xerama.worker.job_worker import JobWorker


async def _project(session) -> str:
    project = await SQLAlchemyProjectRepository(session).create("p")
    await session.commit()
    return project.id


def _worker(session, **kwargs) -> JobWorker:
    return JobWorker(job_repo=SQLAlchemyJobRepository(session), worker_id="worker-1", **kwargs)


async def test_run_once_returns_false_when_queue_empty(session) -> None:
    worker = _worker(session)
    assert await worker.run_once() is False


async def test_run_once_dispatches_to_registered_handler_and_succeeds(session) -> None:
    project_id = await _project(session)
    job_repo = SQLAlchemyJobRepository(session)
    job = await job_repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={"prompt": "x"})
    await session.commit()

    worker = _worker(session)
    calls = []

    async def handler(claimed_job):
        calls.append(claimed_job.id)
        return ["asset-1"]

    worker.register_handler(JobStage.CONCEPT_GENERATION, handler)
    processed = await worker.run_once()
    await session.commit()

    assert processed is True
    assert calls == [job.id]
    fetched = await job_repo.get(job.id)
    assert fetched.status == JobStatus.SUCCEEDED
    assert fetched.result_asset_ids == ["asset-1"]


async def test_run_once_dead_letters_when_no_handler_registered(session) -> None:
    project_id = await _project(session)
    job_repo = SQLAlchemyJobRepository(session)
    job = await job_repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={})
    await session.commit()

    worker = _worker(session)
    await worker.run_once()
    await session.commit()

    fetched = await job_repo.get(job.id)
    assert fetched.status == JobStatus.FAILED
    assert "no handler registered" in fetched.error


async def test_run_once_requeues_on_retriable_provider_error(session) -> None:
    project_id = await _project(session)
    job_repo = SQLAlchemyJobRepository(session)
    job = await job_repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={}, max_attempts=3)
    await session.commit()

    worker = _worker(session)

    async def handler(claimed_job):
        raise ProviderError(ProviderErrorKind.TIMEOUT, "provider timed out")

    worker.register_handler(JobStage.CONCEPT_GENERATION, handler)
    await worker.run_once()
    await session.commit()

    fetched = await job_repo.get(job.id)
    assert fetched.status == JobStatus.QUEUED
    assert fetched.attempt == 2


async def test_run_once_dead_letters_on_non_retriable_provider_error(session) -> None:
    project_id = await _project(session)
    job_repo = SQLAlchemyJobRepository(session)
    job = await job_repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={})
    await session.commit()

    worker = _worker(session)

    async def handler(claimed_job):
        raise ProviderError(ProviderErrorKind.AUTHENTICATION, "bad api key")

    worker.register_handler(JobStage.CONCEPT_GENERATION, handler)
    await worker.run_once()
    await session.commit()

    fetched = await job_repo.get(job.id)
    assert fetched.status == JobStatus.FAILED
    assert fetched.error == "bad api key"


async def test_run_once_dead_letters_on_unexpected_exception(session) -> None:
    project_id = await _project(session)
    job_repo = SQLAlchemyJobRepository(session)
    job = await job_repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={})
    await session.commit()

    worker = _worker(session)

    async def handler(claimed_job):
        raise ValueError("bug")

    worker.register_handler(JobStage.CONCEPT_GENERATION, handler)
    await worker.run_once()
    await session.commit()

    fetched = await job_repo.get(job.id)
    assert fetched.status == JobStatus.FAILED  # never retried blindly


async def test_reclaim_abandoned_delegates_to_repository(session) -> None:
    project_id = await _project(session)
    job_repo = SQLAlchemyJobRepository(session)
    job = await job_repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={})
    await session.commit()
    await job_repo.claim("some-other-worker", lease_seconds=-1)
    await session.commit()

    worker = _worker(session)
    recovered = await worker.reclaim_abandoned()
    await session.commit()
    assert [r.id for r in recovered] == [job.id]


async def test_run_forever_processes_jobs_and_stops_on_event(session) -> None:
    project_id = await _project(session)
    job_repo = SQLAlchemyJobRepository(session)
    job = await job_repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={})
    await session.commit()

    worker = _worker(session, poll_interval_seconds=0.01, concurrency=1)
    processed = []

    async def handler(claimed_job):
        processed.append(claimed_job.id)
        return []

    worker.register_handler(JobStage.CONCEPT_GENERATION, handler)

    stop_event = asyncio.Event()

    async def _stop_soon():
        await asyncio.sleep(0.05)
        stop_event.set()

    await asyncio.gather(worker.run_forever(stop_event), _stop_soon())
    assert processed == [job.id]
