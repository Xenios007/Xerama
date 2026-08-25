"""Provider ranking / optimization recommendations endpoint (MODULE-064)."""

from fastapi import APIRouter, Depends

from xerama.api.deps import get_optimization_service
from xerama.pipeline.provider_ranking import Objective, ProviderRanking
from xerama.services.optimization_service import OptimizationService

router = APIRouter(tags=["optimization"])


@router.get("/projects/{project_id}/provider-rankings", response_model=list[ProviderRanking])
async def get_provider_rankings(
    project_id: str,
    objective: Objective = "balanced",
    service: OptimizationService = Depends(get_optimization_service),
) -> list[ProviderRanking]:
    """See MODULE-064 - `objective` is one of quality/budget/speed/
    balanced; every ranking carries its raw evidence (accepted rate,
    cost, latency, QC score) alongside the composite score."""
    return await service.rank_providers(project_id, objective)
