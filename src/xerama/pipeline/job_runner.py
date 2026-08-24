"""Shared `GenerationJob` wrapper. See docs/ARCHITECTURE.md section 11, ADR-023.

Used by every stage-orchestrating component (`Showrunner`, `EpisodeEngine`)
so job bookkeeping (create/start/succeed/fail) lives in exactly one place.
"""

from collections.abc import Awaitable, Coroutine
from typing import TypeVar

from xerama.domain.enums import JobStage
from xerama.repositories.interfaces import JobRepository

T = TypeVar("T")


class JobRunner:
    def __init__(self, job_repo: JobRepository) -> None:
        self._job_repo = job_repo

    async def run(
        self,
        project_id: str,
        stage: JobStage,
        model_label: str,
        awaitable: Coroutine[None, None, T] | Awaitable[T],
    ) -> T:
        job = await self._job_repo.create(project_id, stage)
        await self._job_repo.start(job.id, provider="openrouter", model=model_label)
        try:
            result = await awaitable
        except Exception as exc:
            await self._job_repo.fail(job.id, str(exc))
            raise
        await self._job_repo.succeed(job.id)
        return result
