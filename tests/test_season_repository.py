import pytest

import fixtures as fx
from xerama.domain.enums import QCStatus
from xerama.domain.quality import QCResult
from xerama.domain.season import SeasonPlan
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyProjectRepository,
    SQLAlchemySeasonRepository,
    SQLAlchemySeriesRepository,
)

from test_repositories import _brief, _candidate


def _qc(status: QCStatus = QCStatus.PASS) -> QCResult:
    return QCResult(gate="season", status=status, score=10.0 if status == QCStatus.PASS else 0.0)


async def _series(session):
    project = await SQLAlchemyProjectRepository(session).create("p")
    series_repo = SQLAlchemySeriesRepository(session)
    return await series_repo.create_series(project.id, _brief(), _candidate("T"))


@pytest.mark.asyncio
async def test_create_plan_increments_version(session) -> None:
    series = await _series(session)
    repo = SQLAlchemySeasonRepository(session)
    plan = SeasonPlan.model_validate(fx.season_plan())

    v1 = await repo.create_plan(series.id, plan, _qc())
    v2 = await repo.create_plan(series.id, plan, _qc())
    await session.commit()

    assert v1.version == 1
    assert v2.version == 2
    assert v1.id != v2.id


@pytest.mark.asyncio
async def test_get_current_plan_falls_back_to_latest_draft(session) -> None:
    series = await _series(session)
    repo = SQLAlchemySeasonRepository(session)
    plan = SeasonPlan.model_validate(fx.season_plan())

    await repo.create_plan(series.id, plan, _qc())
    await repo.create_plan(series.id, plan, _qc())
    await session.commit()

    current = await repo.get_current_plan(series.id)
    assert current is not None
    assert current.version == 2
    assert current.status == "draft"


@pytest.mark.asyncio
async def test_get_current_plan_prefers_approved_over_later_draft(session) -> None:
    series = await _series(session)
    repo = SQLAlchemySeasonRepository(session)
    plan = SeasonPlan.model_validate(fx.season_plan())

    await repo.create_plan(series.id, plan, _qc())  # version 1
    await repo.approve_version(series.id, 1)
    await repo.create_plan(series.id, plan, _qc())  # version 2, still draft
    await session.commit()

    current = await repo.get_current_plan(series.id)
    assert current.version == 1
    assert current.status == "approved"


@pytest.mark.asyncio
async def test_get_current_plan_none_when_no_plans_exist(session) -> None:
    series = await _series(session)
    repo = SQLAlchemySeasonRepository(session)
    assert await repo.get_current_plan(series.id) is None


@pytest.mark.asyncio
async def test_get_version_and_list_versions(session) -> None:
    series = await _series(session)
    repo = SQLAlchemySeasonRepository(session)
    plan = SeasonPlan.model_validate(fx.season_plan())

    await repo.create_plan(series.id, plan, _qc(QCStatus.BLOCK))
    await repo.create_plan(series.id, plan, _qc(QCStatus.PASS))
    await session.commit()

    versions = await repo.list_versions(series.id)
    assert [v.version for v in versions] == [1, 2]
    assert versions[0].qc_status == "block"
    assert versions[1].qc_status == "pass"

    fetched = await repo.get_version(series.id, 1)
    assert fetched is not None
    assert fetched.qc_status == "block"
    assert await repo.get_version(series.id, 99) is None


@pytest.mark.asyncio
async def test_approve_unknown_version_raises(session) -> None:
    series = await _series(session)
    repo = SQLAlchemySeasonRepository(session)
    with pytest.raises(ValueError):
        await repo.approve_version(series.id, 1)
