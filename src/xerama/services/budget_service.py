"""Project budget ceiling enforcement (MODULE-068).

Distinct from `pipeline/cost_aggregation.py` (ADR-024's cost-per-
accepted-output ratio, an *analysis* metric) - this is a hard gate: has
this project already spent its configured ceiling, full stop. Counts
every attempt's known cost, not just accepted outputs, since a rejected
generation still cost real money and must count against the ceiling.
"""

from xerama.repositories.interfaces import CostRecordRepository


class BudgetExceededError(RuntimeError):
    pass


class BudgetGuard:
    def __init__(self, cost_repo: CostRecordRepository) -> None:
        self._cost_repo = cost_repo

    async def check_budget(self, project_id: str, ceiling_usd: float | None) -> None:
        """No-op if `ceiling_usd` is `None` (unlimited - the standard-
        mode default). Otherwise sums every cost-known record for this
        project and raises `BudgetExceededError` once that total meets
        or exceeds the ceiling."""
        if ceiling_usd is None:
            return
        records = await self._cost_repo.list_by_project(project_id)
        spent = sum(r.cost_usd for r in records if r.cost_known and r.cost_usd is not None)
        if spent >= ceiling_usd:
            raise BudgetExceededError(
                f"project {project_id!r} has spent ${spent:.4f} of its ${ceiling_usd:.4f} budget ceiling"
            )
