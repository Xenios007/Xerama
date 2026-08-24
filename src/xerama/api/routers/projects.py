"""POST /projects - create a Xerama production workspace. See docs/DATA_MODEL.md Project."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from xerama.api.deps import get_project_repo
from xerama.repositories.interfaces import ProjectRecord, ProjectRepository

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""


@router.post("", response_model=ProjectRecord)
async def create_project(
    payload: CreateProjectRequest, repo: ProjectRepository = Depends(get_project_repo)
) -> ProjectRecord:
    return await repo.create(payload.name, payload.description)


@router.get("/{project_id}", response_model=ProjectRecord)
async def get_project(
    project_id: str, repo: ProjectRepository = Depends(get_project_repo)
) -> ProjectRecord:
    project = await repo.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project
