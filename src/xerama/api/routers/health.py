"""Health/readiness + observability endpoints (MODULE-050)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from xerama.api.authorization import require_project_role
from xerama.api.deps import get_observability_service, get_session
from xerama.domain.enums import ProjectRole
from xerama.services.observability_service import ObservabilityService, ObservabilitySnapshot

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness - the process is up. No dependency on the database or any
    provider, so this never false-negatives because of an unrelated
    outage."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(session: AsyncSession = Depends(get_session)) -> dict:
    """Readiness - the database is actually reachable."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - readiness must never leak internals, just fail closed
        raise HTTPException(status_code=503, detail=f"database unreachable: {type(exc).__name__}") from exc
    return {"status": "ready"}


@router.get(
    "/projects/{project_id}/observability",
    response_model=ObservabilitySnapshot,
    dependencies=[Depends(require_project_role(ProjectRole.VIEWER))],
)
async def get_project_observability(
    project_id: str, service: ObservabilityService = Depends(get_observability_service)
) -> ObservabilitySnapshot:
    """"Where and why a production is stuck" in one call: queue depth,
    average stage duration, and per-provider failure/retry counts."""
    return await service.snapshot(project_id)
