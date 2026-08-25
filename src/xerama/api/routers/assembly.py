"""Episode assembly (MODULE-046) and render versioning (MODULE-047)
endpoints.

"Accepted assets can render into a playable episode automatically" plus
"every final episode can be traced to exact source assets and
regenerated."
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from xerama.api.deps import get_assembly_service, get_episode_repo, get_export_service, get_series_repo
from xerama.api.shot_lookup import episode_context
from xerama.domain.asset import Asset
from xerama.domain.episode_render import EpisodeRender
from xerama.domain.export import VERTICAL_1080_1920
from xerama.domain.quality import QCResult
from xerama.pipeline.assembly_plan_builder import IncompleteProductionError
from xerama.repositories.interfaces import EpisodeRepository, SeriesRepository
from xerama.services.assembly_service import EpisodeAssemblyService
from xerama.services.export_service import VerticalExportService

router = APIRouter(tags=["assembly"])


class StalenessReport(BaseModel):
    stale: bool
    reasons: list[str]


class ExportResponse(BaseModel):
    asset: Asset
    render: EpisodeRender
    validation: QCResult


@router.post("/episodes/{episode_id}/render", response_model=Asset)
async def render_episode(
    episode_id: str,
    service: EpisodeAssemblyService = Depends(get_assembly_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
) -> Asset:
    _, series = await episode_context(episode_id, episode_repo, series_repo)
    try:
        render_asset, _render = await service.render_episode(
            episode_id, series.project_id, series_id=series.id
        )
        return render_asset
    except IncompleteProductionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/episodes/{episode_id}/export", response_model=ExportResponse)
async def export_episode(
    episode_id: str,
    service: VerticalExportService = Depends(get_export_service),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
) -> ExportResponse:
    """MODULE-048 - render (MODULE-046) at the default vertical
    1080x1920 profile and validate the result via ffprobe (duration,
    aspect, streams, corruption) plus subtitle safe-area/reading-speed."""
    _, series = await episode_context(episode_id, episode_repo, series_repo)
    try:
        asset, render, report = await service.export_episode(
            episode_id, series.project_id, series_id=series.id, profile=VERTICAL_1080_1920
        )
        return ExportResponse(asset=asset, render=render, validation=report)
    except IncompleteProductionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/episodes/{episode_id}/renders", response_model=list[EpisodeRender])
async def list_episode_renders(
    episode_id: str, service: EpisodeAssemblyService = Depends(get_assembly_service)
) -> list[EpisodeRender]:
    return await service.list_renders(episode_id)


@router.get("/episodes/{episode_id}/renders/current", response_model=EpisodeRender)
async def get_current_episode_render(
    episode_id: str, service: EpisodeAssemblyService = Depends(get_assembly_service)
) -> EpisodeRender:
    render = await service.get_current(episode_id)
    if render is None:
        raise HTTPException(status_code=404, detail="no approved render for this episode yet")
    return render


@router.get("/episode-renders/{render_id}", response_model=EpisodeRender)
async def get_episode_render(
    render_id: str, service: EpisodeAssemblyService = Depends(get_assembly_service)
) -> EpisodeRender:
    try:
        return await service.get_render(render_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/episode-renders/{render_id}/approve", response_model=EpisodeRender)
async def approve_episode_render(
    render_id: str, service: EpisodeAssemblyService = Depends(get_assembly_service)
) -> EpisodeRender:
    """Also how rollback works - approving an older `superseded` render
    (from `GET /episodes/{id}/renders`) makes it current again."""
    try:
        return await service.approve_render(render_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/episode-renders/{render_id}/staleness", response_model=StalenessReport)
async def get_episode_render_staleness(
    render_id: str, service: EpisodeAssemblyService = Depends(get_assembly_service)
) -> StalenessReport:
    try:
        stale, reasons = await service.check_staleness(render_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return StalenessReport(stale=stale, reasons=reasons)
