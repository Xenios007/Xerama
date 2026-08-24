"""Local job worker (MODULE-042).

Claims queued `GenerationJob`s (MODULE-041) and dispatches them to a
stage-handler registry, keeping long media/LLM generation out of the HTTP
request/response cycle. Depends only on the `JobRepository` Protocol, so a
future Redis/Celery/RQ-backed queue can replace `SQLAlchemyJobRepository`
without this worker changing at all.

Retry/backoff (MODULE-043) reuses the existing `ProviderError`/
`ProviderErrorKind` taxonomy (Module 06/07) rather than inventing a second
error-classification system: a handler that raises `ProviderError` gets its
`.retriable` flag honored by `JobRepository.fail_job_attempt`; any other
exception is treated as non-retriable (dead-lettered immediately - an
unexpected bug retrying blindly is rarely correct). Idempotency for
handlers that ingest media leans on Module 04's content-addressed storage:
re-running a handler after a crash never double-writes bytes, only ever
adds a new `Asset` row pointing at the same already-stored content.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from xerama.domain.enums import JobStage
from xerama.providers.errors import ProviderError
from xerama.repositories.interfaces import JobRecord, JobRepository

logger = logging.getLogger("xerama.worker")

StageHandler = Callable[[JobRecord], Awaitable[list[str]]]

DEFAULT_POLL_INTERVAL_SECONDS = 1.0
DEFAULT_LEASE_SECONDS = 60


class JobWorker:
    def __init__(
        self,
        job_repo: JobRepository,
        worker_id: str,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
        concurrency: int = 1,
    ) -> None:
        self._job_repo = job_repo
        self._worker_id = worker_id
        self._poll_interval_seconds = poll_interval_seconds
        self._lease_seconds = lease_seconds
        self._concurrency = concurrency
        self._handlers: dict[JobStage, StageHandler] = {}

    def register_handler(self, stage: JobStage, handler: StageHandler) -> None:
        self._handlers[stage] = handler

    async def reclaim_abandoned(self) -> list[JobRecord]:
        return await self._job_repo.recover_abandoned()

    async def run_once(self) -> bool:
        """Claims and processes at most one job. Returns `True` if a job
        was claimed (regardless of whether it ultimately succeeded or
        failed), `False` if the queue had nothing eligible."""
        job = await self._job_repo.claim(self._worker_id, self._lease_seconds)
        if job is None:
            return False
        await self._process(job)
        return True

    async def _process(self, job: JobRecord) -> None:
        handler = self._handlers.get(job.stage)
        if handler is None:
            logger.warning("no handler registered for stage=%s job=%s", job.stage.value, job.id)
            await self._job_repo.fail_job_attempt(
                job.id, f"no handler registered for stage {job.stage.value}", retriable=False
            )
            return
        try:
            result_asset_ids = await handler(job)
        except ProviderError as exc:
            logger.warning(
                "job %s failed (provider error, retriable=%s): %s", job.id, exc.retriable, exc.message
            )
            await self._job_repo.fail_job_attempt(job.id, exc.message, retriable=exc.retriable)
        except Exception as exc:  # noqa: BLE001 - dead-letter, never retry an unclassified bug blindly
            logger.exception("job %s failed with an unexpected error", job.id)
            await self._job_repo.fail_job_attempt(job.id, str(exc), retriable=False)
        else:
            await self._job_repo.succeed_job(job.id, result_asset_ids)

    async def run_forever(self, stop_event: asyncio.Event | None = None) -> None:
        """Runs `concurrency` claim/process lanes until `stop_event` is set
        - graceful shutdown finishes the in-flight job in each lane rather
        than abandoning it mid-handler."""
        stop_event = stop_event or asyncio.Event()
        await self.reclaim_abandoned()
        await asyncio.gather(*(self._lane(stop_event) for _ in range(self._concurrency)))

    async def _lane(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            processed = await self.run_once()
            if not processed:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=self._poll_interval_seconds)
                except TimeoutError:
                    pass
