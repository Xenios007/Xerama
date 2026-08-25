"""Human feedback endpoints (MODULE-065)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from xerama.api.authorization import (
    authorize_project_access,
    get_current_user,
    get_project_membership_repo,
    require_project_role,
)
from xerama.api.deps import get_asset_service, get_feedback_service
from xerama.domain.auth import User
from xerama.domain.enums import ProjectRole
from xerama.domain.feedback import HumanFeedback
from xerama.repositories.interfaces import ProjectMembershipRepository
from xerama.services.asset_service import AssetService
from xerama.services.feedback_service import HumanFeedbackService

router = APIRouter(tags=["feedback"])


async def _authorize_for_asset(
    asset_id: str,
    min_role: ProjectRole,
    asset_service: AssetService,
    user: User | None,
    membership_repo: ProjectMembershipRepository,
) -> None:
    asset = await asset_service.get(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    await authorize_project_access(asset.ownership.project_id, min_role, user, membership_repo)


class RecordFeedbackRequest(BaseModel):
    decision: str  # "approved" | "rejected" | "retake_requested" | "edited"
    reason: str = ""
    rating: int | None = None
    tags: list[str] = []
    reviewer: str = ""


@router.post("/assets/{asset_id}/feedback", response_model=HumanFeedback)
async def record_asset_feedback(
    asset_id: str,
    body: RecordFeedbackRequest,
    service: HumanFeedbackService = Depends(get_feedback_service),
    asset_service: AssetService = Depends(get_asset_service),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> HumanFeedback:
    """"Human decisions become reusable evaluation data" - independent of
    (and may accompany) `POST /assets/{id}/accept`/`reject`: a rating/tag
    can be recorded even for an asset that's already been accepted."""
    await _authorize_for_asset(asset_id, ProjectRole.EDITOR, asset_service, user, membership_repo)
    try:
        return await service.record(
            asset_id,
            body.decision,
            reason=body.reason,
            rating=body.rating,
            tags=body.tags,
            reviewer=body.reviewer,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/assets/{asset_id}/feedback", response_model=list[HumanFeedback])
async def list_asset_feedback(
    asset_id: str,
    service: HumanFeedbackService = Depends(get_feedback_service),
    asset_service: AssetService = Depends(get_asset_service),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> list[HumanFeedback]:
    await _authorize_for_asset(asset_id, ProjectRole.VIEWER, asset_service, user, membership_repo)
    return await service.list_by_asset(asset_id)


@router.get(
    "/projects/{project_id}/feedback",
    response_model=list[HumanFeedback],
    dependencies=[Depends(require_project_role(ProjectRole.VIEWER))],
)
async def list_project_feedback(
    project_id: str, service: HumanFeedbackService = Depends(get_feedback_service)
) -> list[HumanFeedback]:
    """"Provide export/query for later evaluation" - every review
    decision ever recorded for the project, in one call."""
    return await service.list_by_project(project_id)
