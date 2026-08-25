"""AI evaluation harness endpoints (MODULE-072).

Not project-scoped - a benchmark run compares a *model role*
(`ModelRole`), not any single user's production data, so project-role
authorization does not apply (same reasoning as `GET /jobs/queued` in
MODULE-067). In hosted mode this still requires *some* authenticated
caller (a live run spends real provider credits) - never an invented
project/admin-role check for an endpoint with no natural project owner.
"""

from fastapi import APIRouter, Depends, HTTPException

from xerama.api.authorization import get_current_user
from xerama.api.deps import get_eval_service
from xerama.config import get_settings
from xerama.domain.auth import User
from xerama.domain.enums import ModelRole
from xerama.domain.eval import EvalRunResult
from xerama.pipeline.eval_aggregation import ModelRoleBenchmark
from xerama.services.eval_service import EvalService

router = APIRouter(prefix="/eval", tags=["eval"])


async def _require_authenticated_in_hosted_mode(user: User | None = Depends(get_current_user)) -> None:
    if get_settings().xerama_mode == "hosted" and user is None:
        raise HTTPException(status_code=401, detail="authentication required")


@router.post(
    "/roles/{role}/run",
    response_model=list[EvalRunResult],
    dependencies=[Depends(_require_authenticated_in_hosted_mode)],
)
async def run_eval_dataset(role: ModelRole, service: EvalService = Depends(get_eval_service)) -> list[EvalRunResult]:
    """"Live eval opt-in" - this is the only way a benchmark run
    happens; nothing triggers it automatically. Runs the current
    role -> model assignment (`config.py`) against every case in the
    versioned dataset (`eval/datasets.py`) and persists each result."""
    return await service.run_dataset(role)


@router.get("/roles/{role}/benchmark", response_model=list[ModelRoleBenchmark])
async def get_role_benchmark(
    role: ModelRole, service: EvalService = Depends(get_eval_service)
) -> list[ModelRoleBenchmark]:
    """"Compare models by logical role, not one global winner" - every
    provider/model that has ever been run against this role's dataset,
    grouped and summarized separately."""
    return await service.benchmark_for_role(role)


@router.post("/runs/{run_id}/human-preference", response_model=EvalRunResult)
async def record_human_preference(
    run_id: str, preference: str, service: EvalService = Depends(get_eval_service)
) -> EvalRunResult:
    """Human preference is never inferred - a reviewer explicitly marks
    a run "preferred"/"rejected" after reading it, distinct from the
    harness's own automated schema/quality checks."""
    try:
        return await service.record_human_preference(run_id, preference)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
