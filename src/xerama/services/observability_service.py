"""Production observability aggregation (MODULE-050).

Deliberately does not track anything new in a parallel system - queue
depth and stage durations come from `GenerationJob` (MODULE-041/ADR-023,
already persisted), provider failure/retry counts come from `CostRecord`
(MODULE-049, already persisted per attempt). This service only reads and
summarizes what already exists.
"""

from pydantic import BaseModel

from xerama.repositories.interfaces import JobRepository
from xerama.services.cost_service import CostRecordService


class StageDuration(BaseModel):
    stage: str
    sample_count: int
    average_seconds: float


class ProviderReliability(BaseModel):
    provider: str
    attempt_count: int
    failure_count: int
    retry_count: int  # attempts with attempt > 1


class ObservabilitySnapshot(BaseModel):
    queue_depth: int
    stage_durations: list[StageDuration]
    provider_reliability: list[ProviderReliability]


class ObservabilityService:
    def __init__(self, job_repo: JobRepository, cost_service: CostRecordService) -> None:
        self._job_repo = job_repo
        self._cost_service = cost_service

    async def queue_depth(self) -> int:
        return len(await self._job_repo.list_queued())

    async def stage_durations(self, project_id: str) -> list[StageDuration]:
        jobs = await self._job_repo.list_by_project(project_id)
        totals: dict[str, float] = {}
        counts: dict[str, int] = {}
        for job in jobs:
            if job.started_at is None or job.finished_at is None:
                continue
            seconds = (job.finished_at - job.started_at).total_seconds()
            stage = job.stage.value
            totals[stage] = totals.get(stage, 0.0) + seconds
            counts[stage] = counts.get(stage, 0) + 1
        return [
            StageDuration(stage=stage, sample_count=counts[stage], average_seconds=totals[stage] / counts[stage])
            for stage in sorted(totals)
        ]

    async def provider_reliability(self, project_id: str) -> list[ProviderReliability]:
        records = await self._cost_service.list_by_project(project_id)
        attempts: dict[str, int] = {}
        failures: dict[str, int] = {}
        retries: dict[str, int] = {}
        for record in records:
            if not record.provider:
                continue
            attempts[record.provider] = attempts.get(record.provider, 0) + 1
            if record.failure_reason:
                failures[record.provider] = failures.get(record.provider, 0) + 1
            if record.attempt > 1:
                retries[record.provider] = retries.get(record.provider, 0) + 1
        return [
            ProviderReliability(
                provider=provider,
                attempt_count=attempts[provider],
                failure_count=failures.get(provider, 0),
                retry_count=retries.get(provider, 0),
            )
            for provider in sorted(attempts)
        ]

    async def snapshot(self, project_id: str) -> ObservabilitySnapshot:
        return ObservabilitySnapshot(
            queue_depth=await self.queue_depth(),
            stage_durations=await self.stage_durations(project_id),
            provider_reliability=await self.provider_reliability(project_id),
        )
