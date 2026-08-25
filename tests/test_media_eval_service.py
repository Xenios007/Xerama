from xerama.domain.asset import AssetType
from xerama.domain.enums import MediaQCDimension, QCStatus, ShotClass
from xerama.domain.quality import QCResult
from xerama.eval.media_datasets import DATASET_VERSION, IMAGE_CASES, cases_for_asset_type
from xerama.pipeline.media_eval_harness import MediaEvalHarness
from xerama.providers.errors import ProviderError, ProviderErrorKind
from xerama.providers.fake_image import FakeImageProvider
from xerama.providers.fake_media_qc import FakeMediaQCProvider
from xerama.repositories.sqlalchemy_impl import SQLAlchemyAssetRepository, SQLAlchemyMediaEvalRunRepository
from xerama.services.asset_service import AssetService
from xerama.services.media_eval_service import MediaEvalService
from xerama.services.media_router import MediaProviderRouter


def _harness(session, tmp_path, image_provider=None, media_qc_provider=None) -> MediaEvalHarness:
    from xerama.providers.local_storage import LocalStorageProvider

    return MediaEvalHarness(
        image_router=MediaProviderRouter([image_provider or FakeImageProvider()]),
        video_router=MediaProviderRouter([]),
        media_qc_provider=media_qc_provider or FakeMediaQCProvider(),
        asset_service=AssetService(
            storage=LocalStorageProvider(tmp_path / "storage"),
            asset_repo=SQLAlchemyAssetRepository(session),
        ),
    )


def _identity_case():
    return next(c for c in IMAGE_CASES if c.shot_class == ShotClass.IDENTITY)


# --- harness (session-backed - persists an Asset) --------------------------


async def test_harness_run_case_persists_an_asset_and_accepts_on_pass(session, tmp_path) -> None:
    harness = _harness(session, tmp_path)  # FakeMediaQCProvider defaults to PASS
    outcome = await harness.run_case(_identity_case(), DATASET_VERSION)
    await session.commit()

    assert outcome.generation_succeeded is True
    assert outcome.accepted is True
    assert outcome.asset_id
    assert outcome.provider == "fake_image"
    assert all(r.status == QCStatus.PASS.value for r in outcome.qc_results)


async def test_harness_run_case_rejects_on_a_blocking_qc_result(session, tmp_path) -> None:
    media_qc = FakeMediaQCProvider(
        [QCResult(gate=MediaQCDimension.IDENTITY.value, status=QCStatus.BLOCK, score=2.0, reasons=["mismatch"])]
    )
    harness = _harness(session, tmp_path, media_qc_provider=media_qc)
    outcome = await harness.run_case(_identity_case(), DATASET_VERSION)
    await session.commit()

    assert outcome.generation_succeeded is True
    assert outcome.accepted is False


async def test_harness_run_case_survives_a_qc_provider_failure(session, tmp_path) -> None:
    """A QC scoring failure must not crash the whole run - see the
    harness's own comment on this."""
    media_qc = FakeMediaQCProvider([ProviderError(ProviderErrorKind.TIMEOUT, "qc timed out")])
    harness = _harness(session, tmp_path, media_qc_provider=media_qc)
    outcome = await harness.run_case(_identity_case(), DATASET_VERSION)
    await session.commit()

    assert outcome.generation_succeeded is True
    assert outcome.accepted is False
    assert outcome.qc_results[0].status == "error"


async def test_harness_run_case_records_no_eligible_provider(tmp_path) -> None:
    from xerama.providers.local_storage import LocalStorageProvider

    harness = MediaEvalHarness(
        image_router=MediaProviderRouter([]),  # nothing registered
        video_router=MediaProviderRouter([]),
        media_qc_provider=FakeMediaQCProvider(),
        asset_service=AssetService(storage=LocalStorageProvider(tmp_path / "storage"), asset_repo=None),
    )
    outcome = await harness.run_case(_identity_case(), DATASET_VERSION)

    assert outcome.generation_succeeded is False
    assert outcome.provider == ""
    assert outcome.error


# --- service + repository (real DB via the `session` fixture) --------------


async def test_run_dataset_persists_one_result_per_case(session, tmp_path) -> None:
    harness = _harness(session, tmp_path)
    service = MediaEvalService(harness=harness, repo=SQLAlchemyMediaEvalRunRepository(session))

    results = await service.run_dataset(AssetType.IMAGE)
    await session.commit()

    assert len(results) == len(cases_for_asset_type(AssetType.IMAGE))
    assert all(r.id for r in results)
    assert all(r.accepted for r in results)  # FakeMediaQCProvider defaults to PASS


async def test_benchmark_by_shot_class_aggregates_persisted_runs(session, tmp_path) -> None:
    harness = _harness(session, tmp_path)
    service = MediaEvalService(harness=harness, repo=SQLAlchemyMediaEvalRunRepository(session))

    await service.run_dataset(AssetType.IMAGE)
    await session.commit()

    benchmarks = await service.benchmark_by_shot_class()
    covered_classes = {b.shot_class for b in benchmarks}
    assert covered_classes == {c.shot_class for c in cases_for_asset_type(AssetType.IMAGE)}


async def test_record_human_preference_updates_the_persisted_run(session, tmp_path) -> None:
    harness = _harness(session, tmp_path)
    repo = SQLAlchemyMediaEvalRunRepository(session)
    service = MediaEvalService(harness=harness, repo=repo)

    results = await service.run_dataset(AssetType.IMAGE)
    await session.commit()

    updated = await service.record_human_preference(results[0].id, "preferred")
    await session.commit()

    assert updated.human_preference == "preferred"
