import pytest

from xerama.domain.asset import Asset, AssetOwnership, AssetProvenance, AssetType
from xerama.domain.cost import CostRecord
from xerama.domain.enums import ModelRole, ProviderErrorKind
from xerama.pipeline.ai_gateway import AIGateway, XeramaGenerationError
from xerama.pipeline.cost_aggregation import cost_per_episode, summarize_cost_per_accepted
from xerama.providers.errors import ProviderError
from xerama.providers.fake import FakeLLMProvider
from xerama.repositories.sqlalchemy_impl import SQLAlchemyCostRecordRepository
from xerama.services.cost_service import CostRecordService


def _record(**overrides) -> CostRecord:
    fields = dict(
        id="R1",
        provider="p",
        model="m",
        stage="image_generation",
        unit="images",
        quantity=1.0,
        cost_usd=0.02,
        cost_known=True,
    )
    fields.update(overrides)
    return CostRecord(**fields)


# --- pure aggregation --------------------------------------------------


def test_summarize_cost_per_accepted_images_counts_accepted_only() -> None:
    records = [
        _record(id="R1", asset_id="A1", cost_usd=0.02),
        _record(id="R2", asset_id="A2", cost_usd=0.02),  # rejected, still costs
        _record(id="R3", asset_id=None, cost_usd=0.02),  # never became an asset
    ]
    result = summarize_cost_per_accepted(records, "images", accepted_asset_ids={"A1"})
    assert result.total_known_cost_usd == pytest.approx(0.06)
    assert result.accepted_quantity == 1.0
    assert result.cost_per_accepted_unit_usd == pytest.approx(0.06)


def test_summarize_cost_per_accepted_seconds_sums_accepted_duration() -> None:
    records = [
        _record(id="R1", unit="seconds", quantity=5.0, asset_id="V1", cost_usd=0.10),
        _record(id="R2", unit="seconds", quantity=5.0, asset_id="V2", cost_usd=0.10),
    ]
    result = summarize_cost_per_accepted(records, "seconds", accepted_asset_ids={"V1"})
    assert result.total_known_cost_usd == pytest.approx(0.20)
    assert result.accepted_quantity == 5.0
    assert result.cost_per_accepted_unit_usd == pytest.approx(0.04)


def test_summarize_cost_per_accepted_with_no_accepted_outputs_has_no_ratio() -> None:
    records = [_record(asset_id="A1", cost_usd=0.02)]
    result = summarize_cost_per_accepted(records, "images", accepted_asset_ids=set())
    assert result.accepted_quantity == 0.0
    assert result.cost_per_accepted_unit_usd is None


def test_summarize_cost_per_accepted_tracks_unknown_cost_separately() -> None:
    records = [
        _record(id="R1", asset_id="A1", cost_usd=None, cost_known=False),
        _record(id="R2", asset_id="A2", cost_usd=0.02, cost_known=True),
    ]
    result = summarize_cost_per_accepted(records, "images", accepted_asset_ids={"A1", "A2"})
    assert result.unknown_cost_attempts == 1
    assert result.total_known_cost_usd == pytest.approx(0.02)  # unknown excluded from the total
    assert result.accepted_quantity == 2.0  # both still count as accepted outputs


def test_cost_per_episode_groups_and_excludes_unknown() -> None:
    records = [
        _record(id="R1", episode_id="EP1", cost_usd=0.02, cost_known=True),
        _record(id="R2", episode_id="EP1", cost_usd=0.03, cost_known=True),
        _record(id="R3", episode_id="EP2", cost_usd=0.05, cost_known=True),
        _record(id="R4", episode_id="EP1", cost_usd=None, cost_known=False),
        _record(id="R5", episode_id=None, cost_usd=0.02, cost_known=True),
    ]
    totals = cost_per_episode(records)
    assert totals == {"EP1": pytest.approx(0.05), "EP2": pytest.approx(0.05)}


# --- repository + service -----------------------------------------------


async def test_cost_record_repository_create_and_list(session) -> None:
    repo = SQLAlchemyCostRecordRepository(session)
    await repo.create(
        provider="fake_video", model="", stage="video_generation", project_id="P1",
        episode_id="EP1", quantity=5.0, unit="seconds", cost_known=False,
    )
    await repo.create(
        provider="fake_video", model="", stage="video_generation", project_id="P1",
        episode_id="EP2", quantity=5.0, unit="seconds", cost_known=False,
    )
    await session.commit()

    by_project = await repo.list_by_project("P1")
    assert len(by_project) == 2
    by_episode = await repo.list_by_episode("EP1")
    assert len(by_episode) == 1


async def test_record_generation_attempts_records_failures_and_winner(session) -> None:
    service = CostRecordService(repo=SQLAlchemyCostRecordRepository(session))
    asset = Asset(
        id="A1",
        type=AssetType.IMAGE,
        storage_path="ab/abcd.png",
        content_hash="abcd",
        ownership=AssetOwnership(project_id="P1", episode_id="EP1", scene_number=1, shot_number=1),
        provenance=AssetProvenance(
            provider="reliable",
            generation_params={
                "routing_attempts": [
                    {"provider_name": "flaky", "outcome": "failed", "detail": "timeout"},
                    {"provider_name": "reliable", "outcome": "selected", "detail": ""},
                ]
            },
        ),
    )
    await service.record_generation_attempts(
        asset, stage="image_generation", project_id="P1", episode_id="EP1",
        scene_number=1, shot_number=1, quantity=1.0, unit="images",
    )
    await session.commit()

    records = await service.list_by_project("P1")
    assert len(records) == 2
    failed = next(r for r in records if r.provider == "flaky")
    assert failed.asset_id is None
    assert "timeout" in failed.failure_reason
    winner = next(r for r in records if r.provider == "reliable")
    assert winner.asset_id == "A1"
    assert winner.quantity == 1.0


async def test_record_generation_attempts_falls_back_without_routing_attempts(session) -> None:
    service = CostRecordService(repo=SQLAlchemyCostRecordRepository(session))
    asset = Asset(
        id="A1",
        type=AssetType.IMAGE,
        storage_path="ab/abcd.png",
        content_hash="abcd",
        ownership=AssetOwnership(project_id="P1"),
        provenance=AssetProvenance(provider="manual_upload"),
    )
    await service.record_generation_attempts(asset, stage="image_generation", project_id="P1")
    await session.commit()

    records = await service.list_by_project("P1")
    assert len(records) == 1
    assert records[0].provider == "manual_upload"
    assert records[0].asset_id == "A1"


# --- AIGateway hook -------------------------------------------------------


async def test_ai_gateway_records_cost_on_success(session) -> None:
    from pydantic import BaseModel

    from xerama.config import ModelRoleRegistry, Settings

    class Echo(BaseModel):
        value: str

    provider = FakeLLMProvider(['{"value": "ok"}'])
    cost_service = CostRecordService(repo=SQLAlchemyCostRecordRepository(session))
    gateway = AIGateway(
        provider=provider, roles=ModelRoleRegistry(Settings()), cost_recorder=cost_service
    )
    result = await gateway.generate(
        ModelRole.JUDGE, Echo, "system", "user", project_id="P1", episode_id="EP1"
    )
    await session.commit()
    assert result.value == "ok"

    records = await cost_service.list_by_project("P1")
    assert len(records) == 1
    assert records[0].unit == "tokens"
    assert records[0].cost_known is False


async def test_ai_gateway_records_cost_on_non_retriable_failure(session) -> None:
    from pydantic import BaseModel

    from xerama.config import ModelRoleRegistry, Settings

    class Echo(BaseModel):
        value: str

    provider = FakeLLMProvider([ProviderError(ProviderErrorKind.AUTHENTICATION, "bad key")])
    cost_service = CostRecordService(repo=SQLAlchemyCostRecordRepository(session))
    gateway = AIGateway(
        provider=provider, roles=ModelRoleRegistry(Settings()), cost_recorder=cost_service
    )
    with pytest.raises(XeramaGenerationError):
        await gateway.generate(ModelRole.JUDGE, Echo, "system", "user", project_id="P1")
    await session.commit()

    records = await cost_service.list_by_project("P1")
    assert len(records) == 1
    assert "bad key" in records[0].failure_reason


async def test_ai_gateway_without_recorder_does_not_persist(session) -> None:
    from pydantic import BaseModel

    from xerama.config import ModelRoleRegistry, Settings

    class Echo(BaseModel):
        value: str

    provider = FakeLLMProvider(['{"value": "ok"}'])
    gateway = AIGateway(provider=provider, roles=ModelRoleRegistry(Settings()))
    result = await gateway.generate(ModelRole.JUDGE, Echo, "system", "user")
    assert result.value == "ok"

    cost_service = CostRecordService(repo=SQLAlchemyCostRecordRepository(session))
    assert await cost_service.list_by_project("anything") == []
