"""Season & Reveal Engine inspect/regenerate/approve endpoints (Module 01)."""

from fastapi import APIRouter, Depends, HTTPException

from xerama.api.authorization import require_series_role
from xerama.api.deps import get_gateway, get_season_repo, get_series_repo
from xerama.domain.enums import ProjectRole
from xerama.pipeline.ai_gateway import AIGateway, XeramaGenerationError
from xerama.pipeline.season_stage import SeasonStage
from xerama.pipeline.season_validators import SeasonValidator
from xerama.repositories.interfaces import SeasonPlanRecord, SeasonRepository, SeriesRepository

router = APIRouter(prefix="/series", tags=["season"])


@router.get(
    "/{series_id}/season-plan",
    response_model=SeasonPlanRecord,
    dependencies=[Depends(require_series_role(ProjectRole.VIEWER))],
)
async def get_current_season_plan(
    series_id: str, repo: SeasonRepository = Depends(get_season_repo)
) -> SeasonPlanRecord:
    plan = await repo.get_current_plan(series_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="no season plan for this series yet")
    return plan


@router.get(
    "/{series_id}/season-plan/versions",
    response_model=list[SeasonPlanRecord],
    dependencies=[Depends(require_series_role(ProjectRole.VIEWER))],
)
async def list_season_plan_versions(
    series_id: str, repo: SeasonRepository = Depends(get_season_repo)
) -> list[SeasonPlanRecord]:
    return await repo.list_versions(series_id)


@router.get(
    "/{series_id}/season-plan/{version}",
    response_model=SeasonPlanRecord,
    dependencies=[Depends(require_series_role(ProjectRole.VIEWER))],
)
async def get_season_plan_version(
    series_id: str, version: int, repo: SeasonRepository = Depends(get_season_repo)
) -> SeasonPlanRecord:
    plan = await repo.get_version(series_id, version)
    if plan is None:
        raise HTTPException(status_code=404, detail="season plan version not found")
    return plan


@router.post(
    "/{series_id}/season-plan/regenerate",
    response_model=SeasonPlanRecord,
    dependencies=[Depends(require_series_role(ProjectRole.EDITOR))],
)
async def regenerate_season_plan(
    series_id: str,
    season_repo: SeasonRepository = Depends(get_season_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    gateway: AIGateway = Depends(get_gateway),
) -> SeasonPlanRecord:
    series = await series_repo.get_series(series_id)
    if series is None:
        raise HTTPException(status_code=404, detail="series not found")
    bible = await series_repo.get_bible(series_id)
    if bible is None:
        raise HTTPException(status_code=409, detail="series has no approved Series Bible yet")
    cast = await series_repo.get_cast(series_id)
    if not cast.characters:
        raise HTTPException(status_code=409, detail="series has no cast yet")

    try:
        plan = await SeasonStage(gateway).generate_season_plan(bible, cast, series.episode_count_target)
    except XeramaGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    qc = SeasonValidator().validate(plan, cast)
    return await season_repo.create_plan(series_id, plan, qc)


@router.post(
    "/{series_id}/season-plan/{version}/approve",
    response_model=SeasonPlanRecord,
    dependencies=[Depends(require_series_role(ProjectRole.EDITOR))],
)
async def approve_season_plan(
    series_id: str, version: int, repo: SeasonRepository = Depends(get_season_repo)
) -> SeasonPlanRecord:
    try:
        return await repo.approve_version(series_id, version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
