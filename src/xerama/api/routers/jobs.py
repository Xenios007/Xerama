"""Job queue endpoints (MODULE-041). `GET /jobs/{job_id}` (single-job
fetch) already exists in `inspect.py` - not duplicated here."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from xerama.api.deps import get_job_repo
from xerama.domain.enums import JobStage, JobStatus
from xerama.repositories.interfaces import JobRecord, JobRepository

router = APIRouter(prefix="/jobs", tags=["jobs"])


class EnqueueJobRequest(BaseModel):
    project_id: str
    stage: JobStage
    payload: dict = {}
    priority: int = 0
    series_id: str | None = None
    depends_on_job_id: str | None = None
    max_attempts: int = 3


@router.post("/enqueue", response_model=JobRecord)
async def enqueue_job(
    body: EnqueueJobRequest, job_repo: JobRepository = Depends(get_job_repo)
) -> JobRecord:
    try:
        return await job_repo.enqueue(
            body.project_id,
            body.stage,
            body.payload,
            priority=body.priority,
            series_id=body.series_id,
            depends_on_job_id=body.depends_on_job_id,
            max_attempts=body.max_attempts,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("", response_model=list[JobRecord])
async def list_jobs(
    project_id: str | None = None,
    stage: JobStage | None = None,
    status: JobStatus | None = None,
    job_repo: JobRepository = Depends(get_job_repo),
) -> list[JobRecord]:
    """See MODULE-054 - "list/get jobs by project/episode/stage/status."
    `episode_id` filtering isn't supported - `GenerationJob` isn't
    episode-scoped in the schema (only project/series), so this filters
    by project/stage/status; any combination, or none for everything."""
    return await job_repo.list_filtered(project_id=project_id, stage=stage, status=status)


@router.get("/queued", response_model=list[JobRecord])
async def list_queued_jobs(
    stage: JobStage | None = None, job_repo: JobRepository = Depends(get_job_repo)
) -> list[JobRecord]:
    return await job_repo.list_queued(stage)


@router.get("/failed", response_model=list[JobRecord])
async def list_failed_jobs(
    project_id: str | None = None, job_repo: JobRepository = Depends(get_job_repo)
) -> list[JobRecord]:
    return await job_repo.list_failed(project_id)


@router.post("/{job_id}/cancel", response_model=JobRecord)
async def cancel_job(job_id: str, job_repo: JobRepository = Depends(get_job_repo)) -> JobRecord:
    try:
        return await job_repo.cancel(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
