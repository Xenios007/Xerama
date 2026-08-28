"""Project lifecycle endpoints (MODULE-051). See docs/DATA_MODEL.md Project."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from xerama.api.authorization import get_current_user, get_project_membership_repo, require_project_role
from xerama.api.deps import (
    get_asset_service,
    get_episode_render_repo,
    get_episode_repo,
    get_project_repo,
    get_series_repo,
)
from xerama.services.asset_service import AssetService
from xerama.config import get_settings
from xerama.domain.auth import User
from xerama.domain.enums import ProjectRole
from xerama.repositories.interfaces import (
    EpisodeRenderRepository,
    EpisodeRepository,
    ProjectMembershipRepository,
    ProjectRecord,
    ProjectRepository,
    SeriesRepository,
)

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class EpisodeStatusSummary(BaseModel):
    id: str
    episode_number: int
    status: str
    current_render_version: int | None = None


class SeriesStatusSummary(BaseModel):
    id: str
    title: str
    status: str
    episodes: list[EpisodeStatusSummary]


class ProjectStatusResponse(BaseModel):
    project: ProjectRecord
    series: list[SeriesStatusSummary]


class FinishedEpisode(BaseModel):
    """One approved, ready-to-watch episode render - what the Library UI
    lists. `friendly_path` is the `finished_videos/...` mirror copy
    `EpisodeAssemblyService.approve_render` writes; `download_url` is the
    stable asset endpoint every render is still reachable through."""

    episode_id: str
    series_id: str
    series_title: str
    episode_number: int
    render_id: str
    version: int
    render_asset_id: str
    friendly_path: str
    download_url: str
    duration_seconds: float | None
    size_bytes: int | None
    created_at: datetime


@router.post("", response_model=ProjectRecord)
async def create_project(
    payload: CreateProjectRequest,
    repo: ProjectRepository = Depends(get_project_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> ProjectRecord:
    """In "hosted" mode a project must have an owner - creating one
    requires an authenticated caller, who is immediately granted
    `ProjectRole.OWNER`. In "standard" (local single-user) mode this is
    unchanged: no user/membership row is required or created."""
    settings = get_settings()
    if settings.xerama_mode == "hosted" and user is None:
        raise HTTPException(status_code=401, detail="authentication required")
    project = await repo.create(payload.name, payload.description)
    if settings.xerama_mode == "hosted" and user is not None:
        await membership_repo.grant(project.id, user.id, ProjectRole.OWNER)
    return project


@router.get("", response_model=list[ProjectRecord])
async def list_projects(
    repo: ProjectRepository = Depends(get_project_repo),
    user: User | None = Depends(get_current_user),
    membership_repo: ProjectMembershipRepository = Depends(get_project_membership_repo),
) -> list[ProjectRecord]:
    """In hosted mode, only projects the caller is a member of - listing
    every project regardless of ownership would itself be the "guessed
    ID" leak MODULE-067 exists to close, just without needing to guess."""
    if get_settings().xerama_mode != "hosted":
        return await repo.list_all()
    if user is None:
        raise HTTPException(status_code=401, detail="authentication required")
    memberships = await membership_repo.list_by_user(user.id)
    projects = []
    for membership in memberships:
        project = await repo.get(membership.project_id)
        if project is not None:
            projects.append(project)
    return projects


@router.get(
    "/{project_id}",
    response_model=ProjectRecord,
    dependencies=[Depends(require_project_role(ProjectRole.VIEWER))],
)
async def get_project(
    project_id: str, repo: ProjectRepository = Depends(get_project_repo)
) -> ProjectRecord:
    project = await repo.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.patch(
    "/{project_id}",
    response_model=ProjectRecord,
    dependencies=[Depends(require_project_role(ProjectRole.EDITOR))],
)
async def update_project(
    project_id: str, payload: UpdateProjectRequest, repo: ProjectRepository = Depends(get_project_repo)
) -> ProjectRecord:
    try:
        return await repo.update(project_id, name=payload.name, description=payload.description)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/{project_id}/archive",
    response_model=ProjectRecord,
    dependencies=[Depends(require_project_role(ProjectRole.OWNER))],
)
async def archive_project(
    project_id: str, repo: ProjectRepository = Depends(get_project_repo)
) -> ProjectRecord:
    try:
        return await repo.archive(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/{project_id}/status",
    response_model=ProjectStatusResponse,
    dependencies=[Depends(require_project_role(ProjectRole.VIEWER))],
)
async def get_project_status(
    project_id: str,
    project_repo: ProjectRepository = Depends(get_project_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    render_repo: EpisodeRenderRepository = Depends(get_episode_render_repo),
) -> ProjectStatusResponse:
    """"Return current series/production status and active version IDs" -
    one call a frontend project dashboard can render from directly."""
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    series_list = await series_repo.list_by_project(project_id)
    series_summaries = []
    for series in series_list:
        episodes = await episode_repo.list_by_series(series.id)
        episode_summaries = []
        for episode in episodes:
            current_render = await render_repo.get_current(episode.id)
            episode_summaries.append(
                EpisodeStatusSummary(
                    id=episode.id,
                    episode_number=episode.episode_number,
                    status=episode.status,
                    current_render_version=current_render.version if current_render else None,
                )
            )
        series_summaries.append(
            SeriesStatusSummary(
                id=series.id, title=series.title, status=series.status, episodes=episode_summaries
            )
        )
    return ProjectStatusResponse(project=project, series=series_summaries)


@router.get(
    "/{project_id}/finished-episodes",
    response_model=list[FinishedEpisode],
    dependencies=[Depends(require_project_role(ProjectRole.VIEWER))],
)
async def list_finished_episodes(
    project_id: str,
    project_repo: ProjectRepository = Depends(get_project_repo),
    series_repo: SeriesRepository = Depends(get_series_repo),
    episode_repo: EpisodeRepository = Depends(get_episode_repo),
    render_repo: EpisodeRenderRepository = Depends(get_episode_render_repo),
    asset_service: AssetService = Depends(get_asset_service),
) -> list[FinishedEpisode]:
    """Every episode across this project whose *current* render is
    `approved` - the "where do I find my finished video" answer (see
    `EpisodeAssemblyService.approve_render`, which is what populates the
    `finished_videos/` mirror this lists)."""
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    results: list[FinishedEpisode] = []
    for series in await series_repo.list_by_project(project_id):
        for episode in await episode_repo.list_by_series(series.id):
            render = await render_repo.get_current(episode.id)
            if render is None or render.status != "approved":
                continue
            asset = await asset_service.get(render.render_asset_id)
            friendly_path = (
                f"finished_videos/{episode.series_id}/"
                f"episode_{episode.episode_number:02d}_v{render.version}.mp4"
            )
            results.append(
                FinishedEpisode(
                    episode_id=episode.id,
                    series_id=series.id,
                    series_title=series.title,
                    episode_number=episode.episode_number,
                    render_id=render.id,
                    version=render.version,
                    render_asset_id=render.render_asset_id,
                    friendly_path=friendly_path,
                    download_url=f"/assets/{render.render_asset_id}/download",
                    duration_seconds=asset.duration_seconds if asset else None,
                    size_bytes=asset.size_bytes if asset else None,
                    created_at=render.created_at,
                )
            )
    return results
