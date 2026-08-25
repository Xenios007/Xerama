import pytest

from xerama.domain.asset import Asset, AssetOwnership, AssetType
from xerama.domain.enums import MediaQCDimension, QCStatus
from xerama.domain.quality import QCResult
from xerama.pipeline.media_qc_checks import check_dialogue_audio, check_media_health
from xerama.providers.errors import ProviderError, ProviderErrorKind
from xerama.providers.fake_media_qc import FakeMediaQCProvider
from xerama.providers.local_storage import LocalStorageProvider
from xerama.providers.media_qc import MediaQCContext
from xerama.repositories.sqlalchemy_impl import SQLAlchemyAssetRepository, SQLAlchemyMediaQCRepository
from xerama.services.asset_service import AssetService
from xerama.services.media_qc_service import MediaQCService, QCGateBlockedError


@pytest.fixture
def storage(tmp_path):
    return LocalStorageProvider(tmp_path / "store")


def _asset_service(session, storage) -> AssetService:
    return AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session))


def _media_qc(session, storage, provider=None) -> MediaQCService:
    return MediaQCService(
        repo=SQLAlchemyMediaQCRepository(session),
        asset_service=_asset_service(session, storage),
        provider=provider or FakeMediaQCProvider(),
    )


# --- deterministic checks -------------------------------------------------


def _image_asset(**overrides):
    fields = dict(
        id="A1",
        type=AssetType.IMAGE,
        storage_path="ab/abcd.png",
        content_hash="abcd",
        size_bytes=100,
        width=1080,
        height=1920,
        ownership=AssetOwnership(project_id="P1"),
    )
    fields.update(overrides)
    return Asset(**fields)


def test_check_media_health_passes_clean_image() -> None:
    result = check_media_health(_image_asset(), expected_aspect_ratio="9:16")
    assert result.status == QCStatus.PASS
    assert result.score == 10.0
    assert result.reasons == []


def test_check_media_health_blocks_zero_bytes() -> None:
    result = check_media_health(_image_asset(size_bytes=0))
    assert result.status == QCStatus.BLOCK
    assert result.score == 0.0
    assert "zero size_bytes" in result.reasons[0]
    assert result.repair_recommendation


def test_check_media_health_warns_on_missing_dimensions() -> None:
    result = check_media_health(_image_asset(width=None, height=None))
    assert result.status == QCStatus.WARN
    assert "missing width/height" in result.reasons[0]


def test_check_media_health_warns_on_aspect_mismatch() -> None:
    result = check_media_health(_image_asset(width=1920, height=1080), expected_aspect_ratio="9:16")
    assert result.status == QCStatus.WARN
    assert "aspect ratio" in result.reasons[0]


def test_check_media_health_blocks_nonpositive_video_duration() -> None:
    video = _image_asset(type=AssetType.VIDEO, duration_seconds=0.0)
    result = check_media_health(video)
    assert result.status == QCStatus.BLOCK


def test_check_media_health_warns_on_missing_duration() -> None:
    video = _image_asset(type=AssetType.VIDEO, duration_seconds=None)
    result = check_media_health(video)
    assert result.status == QCStatus.WARN


def test_check_media_health_warns_on_duration_deviation() -> None:
    video = _image_asset(type=AssetType.VIDEO, duration_seconds=10.0)
    result = check_media_health(video, expected_duration_seconds=5.0)
    assert result.status == QCStatus.WARN
    assert "deviates" in result.reasons[0]


def test_check_dialogue_audio_warns_when_unmeasured() -> None:
    audio = _image_asset(type=AssetType.AUDIO, duration_seconds=None)
    result = check_dialogue_audio(audio)
    assert result.status == QCStatus.WARN
    assert "no measured duration" in result.reasons[0]


def test_check_dialogue_audio_blocks_negative_duration() -> None:
    audio = _image_asset(type=AssetType.AUDIO, duration_seconds=-1.0)
    result = check_dialogue_audio(audio)
    assert result.status == QCStatus.BLOCK


def test_check_dialogue_audio_passes_matching_duration() -> None:
    audio = _image_asset(type=AssetType.AUDIO, duration_seconds=3.1)
    result = check_dialogue_audio(audio, expected_duration_seconds=3.0)
    assert result.status == QCStatus.PASS


def test_check_dialogue_audio_warns_on_deviation() -> None:
    audio = _image_asset(type=AssetType.AUDIO, duration_seconds=9.0)
    result = check_dialogue_audio(audio, expected_duration_seconds=3.0)
    assert result.status == QCStatus.WARN


# --- FakeMediaQCProvider ---------------------------------------------------


async def test_fake_media_qc_provider_defaults_to_pass() -> None:
    provider = FakeMediaQCProvider()
    asset = _image_asset()
    result = await provider.score(MediaQCDimension.COMPOSITION, asset, b"bytes", [], MediaQCContext())
    assert result.status == QCStatus.PASS
    assert provider.calls == [(MediaQCDimension.COMPOSITION, "A1")]


async def test_fake_media_qc_provider_returns_queued_result() -> None:
    blocked = QCResult(gate="composition", status=QCStatus.BLOCK, score=1.0, reasons=["bad framing"])
    provider = FakeMediaQCProvider([blocked])
    result = await provider.score(MediaQCDimension.COMPOSITION, _image_asset(), b"x", [], MediaQCContext())
    assert result is blocked


async def test_fake_media_qc_provider_raises_queued_error() -> None:
    provider = FakeMediaQCProvider([ProviderError(ProviderErrorKind.TIMEOUT, "boom")])
    with pytest.raises(ProviderError):
        await provider.score(MediaQCDimension.STYLE, _image_asset(), b"x", [], MediaQCContext())


# --- repository -------------------------------------------------------------


async def test_media_qc_repository_create_list_and_get_latest(session, storage) -> None:
    asset_service = _asset_service(session, storage)
    asset = await asset_service.ingest_bytes(b"img", AssetType.IMAGE, AssetOwnership(project_id="P1"))
    await session.commit()

    repo = SQLAlchemyMediaQCRepository(session)
    first = await repo.create(
        asset_id=asset.id,
        dimension=MediaQCDimension.MEDIA_HEALTH,
        status=QCStatus.PASS,
        score=10.0,
        evidence={"size_bytes": 3},
        reasons=[],
    )
    second = await repo.create(
        asset_id=asset.id,
        dimension=MediaQCDimension.MEDIA_HEALTH,
        status=QCStatus.WARN,
        score=5.0,
        evidence={"size_bytes": 3},
        reasons=["stale"],
    )
    await session.commit()

    assert first.id != second.id
    all_attempts = await repo.list_by_asset(asset.id)
    assert [a.id for a in all_attempts] == [first.id, second.id]

    latest = await repo.get_latest(asset.id, MediaQCDimension.MEDIA_HEALTH)
    assert latest.id == second.id
    assert latest.status == QCStatus.WARN

    assert await repo.get_latest(asset.id, MediaQCDimension.STYLE) is None


# --- service ----------------------------------------------------------------


async def test_run_check_media_health_persists_attempt(session, storage) -> None:
    asset_service = _asset_service(session, storage)
    asset = await asset_service.ingest_bytes(b"img", AssetType.IMAGE, AssetOwnership(project_id="P1"))
    await session.commit()

    service = _media_qc(session, storage)
    attempt = await service.run_check(asset.id, MediaQCDimension.MEDIA_HEALTH)
    await session.commit()

    assert attempt.dimension == MediaQCDimension.MEDIA_HEALTH
    assert attempt.status == QCStatus.WARN  # missing width/height metadata
    assert attempt.evidence["size_bytes"] == len(b"img")

    stored = await service.list_attempts(asset.id)
    assert len(stored) == 1


async def test_run_check_vision_dimension_reads_candidate_and_reference_bytes(session, storage) -> None:
    asset_service = _asset_service(session, storage)
    candidate = await asset_service.ingest_bytes(b"candidate", AssetType.IMAGE, AssetOwnership(project_id="P1"))
    reference = await asset_service.ingest_bytes(b"reference", AssetType.IMAGE, AssetOwnership(project_id="P1"))
    await session.commit()

    provider = FakeMediaQCProvider()
    service = _media_qc(session, storage, provider)
    context = MediaQCContext(reference_asset_ids=[reference.id])
    attempt = await service.run_check(candidate.id, MediaQCDimension.IDENTITY, context)
    await session.commit()

    assert attempt.status == QCStatus.PASS
    assert provider.calls == [(MediaQCDimension.IDENTITY, candidate.id)]
    assert attempt.evidence["reference_asset_ids"] == [reference.id]


async def test_run_check_skips_unresolved_reference_asset(session, storage) -> None:
    asset_service = _asset_service(session, storage)
    candidate = await asset_service.ingest_bytes(b"candidate", AssetType.IMAGE, AssetOwnership(project_id="P1"))
    await session.commit()

    service = _media_qc(session, storage)
    context = MediaQCContext(reference_asset_ids=["does-not-exist"])
    attempt = await service.run_check(candidate.id, MediaQCDimension.STYLE, context)
    await session.commit()
    assert attempt.status == QCStatus.PASS  # unresolved reference skipped, not fatal


async def test_run_gate_raises_on_block(session, storage) -> None:
    asset_service = _asset_service(session, storage)
    asset = await asset_service.ingest_bytes(b"img", AssetType.IMAGE, AssetOwnership(project_id="P1"))
    await session.commit()

    blocked = QCResult(gate="composition", status=QCStatus.BLOCK, score=0.0, reasons=["crowded frame"])
    provider = FakeMediaQCProvider([blocked])
    service = _media_qc(session, storage, provider)

    with pytest.raises(QCGateBlockedError) as excinfo:
        await service.run_gate(asset.id, [MediaQCDimension.MEDIA_HEALTH, MediaQCDimension.COMPOSITION])
    await session.commit()

    assert "crowded frame" in str(excinfo.value)
    assert len(excinfo.value.attempts) == 2
    # Both attempts are still persisted even though the gate as a whole failed.
    assert len(await service.list_attempts(asset.id)) == 2


async def test_run_gate_passes_when_no_block(session, storage) -> None:
    asset_service = _asset_service(session, storage)
    asset = await asset_service.ingest_bytes(b"img", AssetType.IMAGE, AssetOwnership(project_id="P1"))
    await session.commit()

    service = _media_qc(session, storage)
    attempts = await service.run_gate(asset.id, [MediaQCDimension.MEDIA_HEALTH, MediaQCDimension.COMPOSITION])
    await session.commit()
    assert len(attempts) == 2
    assert all(a.status != QCStatus.BLOCK for a in attempts)
