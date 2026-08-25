"""Human feedback endpoints (MODULE-065)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from xerama.api.deps import get_feedback_service
from xerama.domain.feedback import HumanFeedback
from xerama.services.feedback_service import HumanFeedbackService

router = APIRouter(tags=["feedback"])


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
) -> HumanFeedback:
    """"Human decisions become reusable evaluation data" - independent of
    (and may accompany) `POST /assets/{id}/accept`/`reject`: a rating/tag
    can be recorded even for an asset that's already been accepted."""
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
    asset_id: str, service: HumanFeedbackService = Depends(get_feedback_service)
) -> list[HumanFeedback]:
    return await service.list_by_asset(asset_id)


@router.get("/projects/{project_id}/feedback", response_model=list[HumanFeedback])
async def list_project_feedback(
    project_id: str, service: HumanFeedbackService = Depends(get_feedback_service)
) -> list[HumanFeedback]:
    """"Provide export/query for later evaluation" - every review
    decision ever recorded for the project, in one call."""
    return await service.list_by_project(project_id)
