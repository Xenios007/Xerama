"""Production cost reporting endpoints (MODULE-049).

"Provider decisions can be based on accepted-output economics rather than
sticker price" - `/costs/summary` computes cost per accepted image,
accepted video second, and total cost per episode (ADR-024).
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from xerama.api.authorization import require_project_role
from xerama.api.deps import get_asset_service, get_cost_service
from xerama.domain.asset import AssetStatus, AssetType
from xerama.domain.cost import CostRecord
from xerama.domain.enums import ProjectRole
from xerama.pipeline.cost_aggregation import AcceptedOutputCost, cost_per_episode, summarize_cost_per_accepted
from xerama.services.asset_service import AssetService
from xerama.services.cost_service import CostRecordService

router = APIRouter(
    prefix="/projects/{project_id}/costs",
    tags=["costs"],
    dependencies=[Depends(require_project_role(ProjectRole.VIEWER))],
)


class CostSummaryResponse(BaseModel):
    image: AcceptedOutputCost
    video: AcceptedOutputCost
    cost_by_episode_usd: dict[str, float]


@router.get("", response_model=list[CostRecord])
async def list_project_costs(
    project_id: str, service: CostRecordService = Depends(get_cost_service)
) -> list[CostRecord]:
    return await service.list_by_project(project_id)


@router.get("/summary", response_model=CostSummaryResponse)
async def get_project_cost_summary(
    project_id: str,
    cost_service: CostRecordService = Depends(get_cost_service),
    asset_service: AssetService = Depends(get_asset_service),
) -> CostSummaryResponse:
    records = await cost_service.list_by_project(project_id)

    accepted_images = await asset_service.list_by_ownership(
        project_id, asset_type=AssetType.IMAGE
    )
    accepted_videos = await asset_service.list_by_ownership(
        project_id, asset_type=AssetType.VIDEO
    )
    accepted_image_ids = {a.id for a in accepted_images if a.status == AssetStatus.ACCEPTED}
    accepted_video_ids = {a.id for a in accepted_videos if a.status == AssetStatus.ACCEPTED}

    return CostSummaryResponse(
        image=summarize_cost_per_accepted(records, "images", accepted_image_ids),
        video=summarize_cost_per_accepted(records, "seconds", accepted_video_ids),
        cost_by_episode_usd=cost_per_episode(records),
    )
