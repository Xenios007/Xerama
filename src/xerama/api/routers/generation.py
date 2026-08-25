"""POST /projects/{id}/generate-series - runs the full XER-001 story pipeline.

See README.md "First end-to-end test". Runs synchronously in-process for
Trial 01 (acceptable per docs/ARCHITECTURE.md section 14 - "a simple
SQLite-backed local worker is acceptable for Trial 01"); each stage is still
recorded as a persistent `GenerationJob` so a mid-pipeline failure leaves
earlier stages inspectable.
"""

from fastapi import APIRouter, Depends, HTTPException

from xerama.api.authorization import require_project_role
from xerama.api.deps import get_project_repo, get_showrunner
from xerama.domain.brief import CreativeBrief
from xerama.domain.enums import ProjectRole
from xerama.pipeline.ai_gateway import XeramaGenerationError
from xerama.pipeline.orchestrator import PipelineResult, Showrunner
from xerama.repositories.interfaces import ProjectRepository

router = APIRouter(prefix="/projects", tags=["generation"])


@router.post(
    "/{project_id}/generate-series",
    response_model=PipelineResult,
    dependencies=[Depends(require_project_role(ProjectRole.EDITOR))],
)
async def generate_series(
    project_id: str,
    brief: CreativeBrief,
    showrunner: Showrunner = Depends(get_showrunner),
    project_repo: ProjectRepository = Depends(get_project_repo),
) -> PipelineResult:
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    try:
        return await showrunner.run(project_id, brief)
    except XeramaGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
