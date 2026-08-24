import asyncio
from datetime import timedelta

import pytest

from xerama.db.base import create_all, make_engine, make_session_factory, utcnow
from xerama.domain.enums import JobStage, JobStatus
from xerama.repositories.sqlalchemy_impl import SQLAlchemyJobRepository, SQLAlchemyProjectRepository


async def _project(session) -> str:
    project = await SQLAlchemyProjectRepository(session).create("p")
    await session.commit()
    return project.id


async def test_enqueue_and_claim(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyJobRepository(session)

    enqueued = await repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={"prompt": "x"})
    await session.commit()
    assert enqueued.status == JobStatus.QUEUED

    claimed = await repo.claim("worker-1")
    await session.commit()
    assert claimed is not None
    assert claimed.id == enqueued.id
    assert claimed.status == JobStatus.RUNNING


async def test_claim_returns_none_when_queue_empty(session) -> None:
    repo = SQLAlchemyJobRepository(session)
    assert await repo.claim("worker-1") is None


async def test_claim_respects_priority_order(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyJobRepository(session)
    await repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={}, priority=0)
    high = await repo.enqueue(project_id, JobStage.JUDGE, payload={}, priority=10)
    await session.commit()

    claimed = await repo.claim("worker-1")
    assert claimed.id == high.id


async def test_claim_is_fifo_within_same_priority(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyJobRepository(session)
    first = await repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={})
    await repo.enqueue(project_id, JobStage.JUDGE, payload={})
    await session.commit()

    claimed = await repo.claim("worker-1")
    assert claimed.id == first.id


async def test_claim_skips_job_not_yet_scheduled(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyJobRepository(session)
    await repo.enqueue(
        project_id, JobStage.CONCEPT_GENERATION, payload={}, scheduled_at=utcnow() + timedelta(hours=1)
    )
    await session.commit()

    assert await repo.claim("worker-1") is None


async def test_claim_respects_unsatisfied_dependency(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyJobRepository(session)
    dependency = await repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={})
    await repo.enqueue(project_id, JobStage.JUDGE, payload={}, depends_on_job_id=dependency.id)
    await session.commit()

    # Only the dependency itself is eligible - the dependent job is skipped.
    claimed = await repo.claim("worker-1")
    assert claimed.id == dependency.id


async def test_claim_allows_dependent_once_dependency_succeeded(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyJobRepository(session)
    dependency = await repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={})
    dependent = await repo.enqueue(project_id, JobStage.JUDGE, payload={}, depends_on_job_id=dependency.id)
    await session.commit()

    await repo.claim("worker-1")  # claims the dependency
    await repo.succeed_job(dependency.id)
    await session.commit()

    claimed = await repo.claim("worker-1")
    assert claimed.id == dependent.id


async def test_heartbeat_extends_lease(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyJobRepository(session)
    job = await repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={})
    await session.commit()
    await repo.claim("worker-1")
    await session.commit()

    await repo.heartbeat(job.id, "worker-1")
    await session.commit()  # must not raise


async def test_heartbeat_rejects_wrong_worker(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyJobRepository(session)
    job = await repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={})
    await session.commit()
    await repo.claim("worker-1")
    await session.commit()

    with pytest.raises(PermissionError):
        await repo.heartbeat(job.id, "worker-2")


async def test_succeed_job_clears_lease_and_records_results(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyJobRepository(session)
    job = await repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={})
    await session.commit()
    await repo.claim("worker-1")
    await session.commit()

    succeeded = await repo.succeed_job(job.id, result_asset_ids=["asset-1"])
    await session.commit()
    assert succeeded.status == JobStatus.SUCCEEDED
    assert succeeded.result_asset_ids == ["asset-1"]
    assert succeeded.lease_owner is None


async def test_fail_job_attempt_requeues_when_retriable_and_attempts_remain(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyJobRepository(session)
    job = await repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={}, max_attempts=3)
    await session.commit()
    await repo.claim("worker-1")
    await session.commit()

    failed = await repo.fail_job_attempt(job.id, "transient timeout", retriable=True)
    await session.commit()
    assert failed.status == JobStatus.QUEUED
    assert failed.attempt == 2
    assert failed.lease_owner is None
    assert failed.error == "transient timeout"


async def test_fail_job_attempt_dead_letters_after_max_attempts(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyJobRepository(session)
    job = await repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={}, max_attempts=1)
    await session.commit()
    await repo.claim("worker-1")
    await session.commit()

    failed = await repo.fail_job_attempt(job.id, "still failing", retriable=True)
    await session.commit()
    assert failed.status == JobStatus.FAILED  # attempt already == max_attempts


async def test_fail_job_attempt_dead_letters_immediately_when_not_retriable(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyJobRepository(session)
    job = await repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={}, max_attempts=5)
    await session.commit()
    await repo.claim("worker-1")
    await session.commit()

    failed = await repo.fail_job_attempt(job.id, "bad request", retriable=False)
    await session.commit()
    assert failed.status == JobStatus.FAILED
    assert failed.attempt == 1


async def test_cancel_terminal_job(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyJobRepository(session)
    job = await repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={})
    await session.commit()

    cancelled = await repo.cancel(job.id)
    await session.commit()
    assert cancelled.status == JobStatus.CANCELLED


async def test_cancel_does_not_reopen_already_succeeded_job(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyJobRepository(session)
    job = await repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={})
    await session.commit()
    await repo.claim("worker-1")
    await repo.succeed_job(job.id)
    await session.commit()

    result = await repo.cancel(job.id)
    assert result.status == JobStatus.SUCCEEDED  # cancel is a no-op on a terminal job


async def test_recover_abandoned_requeues_expired_lease(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyJobRepository(session)
    job = await repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={})
    await session.commit()
    await repo.claim("worker-1", lease_seconds=-1)  # already-expired lease
    await session.commit()

    recovered = await repo.recover_abandoned()
    await session.commit()
    assert [r.id for r in recovered] == [job.id]

    refetched = await repo.get(job.id)
    assert refetched.status == JobStatus.QUEUED
    assert refetched.lease_owner is None


async def test_list_queued_and_list_failed(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyJobRepository(session)
    await repo.enqueue(project_id, JobStage.CONCEPT_GENERATION, payload={})
    failing = await repo.enqueue(project_id, JobStage.JUDGE, payload={}, max_attempts=1)
    await session.commit()
    await repo.claim("worker-1")  # claims the concept-generation job (higher priority tie -> FIFO first)
    await repo.claim("worker-1")  # claims the judge job
    await repo.fail_job_attempt(failing.id, "boom", retriable=False)
    await session.commit()

    queued = await repo.list_queued()
    assert queued == []  # both jobs claimed/terminal
    failed = await repo.list_failed(project_id)
    assert len(failed) == 1
    assert failed[0].id == failing.id


async def test_claim_race_only_one_worker_wins(tmp_path) -> None:
    db_path = tmp_path / "race.db"
    engine = make_engine(f"sqlite+aiosqlite:///{db_path}")
    await create_all(engine)
    session_factory = make_session_factory(engine)

    async with session_factory() as setup_session:
        project = await SQLAlchemyProjectRepository(setup_session).create("p")
        job = await SQLAlchemyJobRepository(setup_session).enqueue(
            project.id, JobStage.CONCEPT_GENERATION, payload={}
        )
        await setup_session.commit()

    async def _claim_with_own_session(worker_id: str):
        async with session_factory() as worker_session:
            result = await SQLAlchemyJobRepository(worker_session).claim(worker_id)
            await worker_session.commit()
            return result

    results = await asyncio.gather(
        _claim_with_own_session("worker-a"), _claim_with_own_session("worker-b")
    )
    winners = [r for r in results if r is not None]
    assert len(winners) == 1
    assert winners[0].id == job.id

    await engine.dispose()
