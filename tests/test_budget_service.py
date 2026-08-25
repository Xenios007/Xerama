import pytest

from xerama.repositories.sqlalchemy_impl import SQLAlchemyCostRecordRepository
from xerama.services.budget_service import BudgetExceededError, BudgetGuard


async def _spend(session, project_id: str, cost_usd: float, cost_known: bool = True) -> None:
    repo = SQLAlchemyCostRecordRepository(session)
    await repo.create(
        provider="p", model="m", stage="image_generation", project_id=project_id,
        cost_usd=cost_usd, cost_known=cost_known,
    )


async def test_check_budget_is_a_no_op_when_ceiling_is_none(session) -> None:
    guard = BudgetGuard(cost_repo=SQLAlchemyCostRecordRepository(session))
    await _spend(session, "P1", 1000.0)
    await session.commit()
    await guard.check_budget("P1", ceiling_usd=None)  # does not raise


async def test_check_budget_allows_spend_under_the_ceiling(session) -> None:
    guard = BudgetGuard(cost_repo=SQLAlchemyCostRecordRepository(session))
    await _spend(session, "P1", 1.0)
    await session.commit()
    await guard.check_budget("P1", ceiling_usd=5.0)  # does not raise


async def test_check_budget_raises_once_the_ceiling_is_met(session) -> None:
    guard = BudgetGuard(cost_repo=SQLAlchemyCostRecordRepository(session))
    await _spend(session, "P1", 3.0)
    await _spend(session, "P1", 2.0)
    await session.commit()
    with pytest.raises(BudgetExceededError):
        await guard.check_budget("P1", ceiling_usd=5.0)


async def test_check_budget_ignores_cost_unknown_records(session) -> None:
    """Never invent a cost for a record marked unknown - the same
    "never invent unavailable metrics" discipline as ADR-024/MODULE-061."""
    guard = BudgetGuard(cost_repo=SQLAlchemyCostRecordRepository(session))
    await _spend(session, "P1", 999.0, cost_known=False)
    await session.commit()
    await guard.check_budget("P1", ceiling_usd=5.0)  # does not raise - the spend is unknown, not zero


async def test_check_budget_is_scoped_per_project(session) -> None:
    guard = BudgetGuard(cost_repo=SQLAlchemyCostRecordRepository(session))
    await _spend(session, "P1", 100.0)
    await session.commit()
    await guard.check_budget("P2", ceiling_usd=5.0)  # a different project - does not raise
