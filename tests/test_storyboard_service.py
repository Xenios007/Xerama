import pytest

from xerama.domain.generation_request import CompiledReferences, ShotGenerationRequest
from xerama.domain.scene import Camera, ProviderRequirements, Visual
from xerama.domain.enums import AudioMode
from xerama.providers.fake_image import FakeImageProvider
from xerama.providers.image import ImageProviderCapabilities
from xerama.providers.local_storage import LocalStorageProvider
from xerama.providers.fake_media_qc import FakeMediaQCProvider
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyAssetRepository,
    SQLAlchemyMediaQCRepository,
    SQLAlchemyStoryboardRepository,
)
from xerama.services.asset_service import AssetService
from xerama.services.media_qc_service import MediaQCService
from xerama.services.media_router import MediaProviderRouter, NoEligibleProviderError
from xerama.services.storyboard_service import StoryboardService


def _media_qc(session, storage, provider=None) -> MediaQCService:
    return MediaQCService(
        repo=SQLAlchemyMediaQCRepository(session),
        asset_service=AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session)),
        provider=provider or FakeMediaQCProvider(),
    )

from test_storyboard_repository import _episode


def _request(**overrides) -> ShotGenerationRequest:
    fields = dict(
        shot_number=1,
        scene_number=1,
        prompt="Mara opens the letter, apartment, night.",
        negative_prompt="extra limbs",
        character_dna=["Mara: brown eyes"],
        duration_seconds=5.0,
        camera=Camera(shot_size="close-up"),
        visual=Visual(),
        audio_mode=AudioMode.NATIVE,
        references=CompiledReferences(character_asset_ids=[]),
        provider_requirements=ProviderRequirements(),
    )
    fields.update(overrides)
    return ShotGenerationRequest(**fields)


def _service(session, storage) -> StoryboardService:
    return StoryboardService(
        storyboard_repo=SQLAlchemyStoryboardRepository(session),
        asset_service=AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session)),
        media_qc=_media_qc(session, storage),
    )


@pytest.fixture
def storage(tmp_path):
    return LocalStorageProvider(tmp_path / "store")


async def test_generate_keyframe_ingests_asset(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    storyboard = await service.get_or_create_storyboard(episode_id, 1, 1)
    await session.commit()

    provider = FakeImageProvider([b"keyframe-bytes"])
    router = MediaProviderRouter([provider])
    asset = await service.generate_keyframe(storyboard.id, "PROJ_1", _request(), router)
    await session.commit()

    assert asset.take_number == 1
    assert asset.status.value == "pending"
    assert await storage.read_bytes(asset.storage_path) == b"keyframe-bytes"


async def test_generate_keyframe_take_numbers_increment_on_retry(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    storyboard = await service.get_or_create_storyboard(episode_id, 1, 1)
    await session.commit()

    provider = FakeImageProvider([b"take-1", b"take-2"])
    router = MediaProviderRouter([provider])
    first = await service.generate_keyframe(storyboard.id, "PROJ_1", _request(), router)
    await session.commit()
    second = await service.generate_keyframe(storyboard.id, "PROJ_1", _request(), router)
    await session.commit()

    assert first.take_number == 1
    assert second.take_number == 2


async def test_generate_keyframe_rejects_unsupported_aspect_ratio(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    storyboard = await service.get_or_create_storyboard(episode_id, 1, 1)
    await session.commit()

    provider = FakeImageProvider(capabilities=ImageProviderCapabilities(supported_aspects=["16:9"]))
    router = MediaProviderRouter([provider])
    with pytest.raises(NoEligibleProviderError):
        await service.generate_keyframe(storyboard.id, "PROJ_1", _request(aspect_ratio="9:16"), router)
    assert provider.calls == []  # rejected before spending a generation request


async def test_generate_keyframe_rejects_when_references_unsupported(session, storage) -> None:
    from xerama.domain.asset import AssetOwnership, AssetType

    episode_id = await _episode(session)
    asset_service = AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session))
    service = StoryboardService(
        storyboard_repo=SQLAlchemyStoryboardRepository(session),
        asset_service=asset_service,
        media_qc=_media_qc(session, storage),
    )
    storyboard = await service.get_or_create_storyboard(episode_id, 1, 1)
    reference_asset = await asset_service.ingest_bytes(
        b"root portrait", AssetType.IMAGE, AssetOwnership(project_id="PROJ_1")
    )
    await session.commit()

    provider = FakeImageProvider(capabilities=ImageProviderCapabilities(supports_reference_images=False))
    router = MediaProviderRouter([provider])
    request = _request(references=CompiledReferences(character_asset_ids=[reference_asset.id]))
    with pytest.raises(NoEligibleProviderError):
        await service.generate_keyframe(storyboard.id, "PROJ_1", request, router)
    assert provider.calls == []  # rejected before spending a generation request


async def test_upload_keyframe_manual_fallback(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    storyboard = await service.get_or_create_storyboard(episode_id, 1, 1)
    await session.commit()

    asset = await service.upload_keyframe(storyboard.id, "PROJ_1", b"uploaded bytes", mime_type="image/png")
    await session.commit()
    assert asset.provenance.provider == "manual_upload"
    assert asset.take_number == 1


async def test_accept_keyframe_marks_storyboard_approved(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    storyboard = await service.get_or_create_storyboard(episode_id, 1, 1)
    await session.commit()

    asset = await service.upload_keyframe(storyboard.id, "PROJ_1", b"data")
    await session.commit()
    approved = await service.accept_keyframe(storyboard.id, asset.id)
    await session.commit()

    assert approved.status == "approved"
    assert approved.approved_keyframe_asset_id == asset.id


async def test_accept_keyframe_blocked_by_qc_gate(session, storage) -> None:
    """MODULE-044 - a BLOCK verdict on any dimension keeps the keyframe
    (and the storyboard) not-accepted."""
    from xerama.domain.enums import QCStatus
    from xerama.domain.quality import QCResult
    from xerama.services.media_qc_service import QCGateBlockedError

    episode_id = await _episode(session)
    blocked = QCResult(gate="composition", status=QCStatus.BLOCK, score=0.0, reasons=["crowded frame"])
    service = StoryboardService(
        storyboard_repo=SQLAlchemyStoryboardRepository(session),
        asset_service=AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session)),
        media_qc=_media_qc(session, storage, FakeMediaQCProvider([blocked])),
    )
    storyboard = await service.get_or_create_storyboard(episode_id, 1, 1)
    await session.commit()

    asset = await service.upload_keyframe(storyboard.id, "PROJ_1", b"data")
    await session.commit()

    with pytest.raises(QCGateBlockedError):
        await service.accept_keyframe(storyboard.id, asset.id)
    await session.commit()

    unchanged = await service.get(storyboard.id)
    assert unchanged.status == "draft"
    asset_service = AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session))
    still_pending = await asset_service.get(asset.id)
    assert still_pending.status.value == "pending"


async def test_reject_keyframe_leaves_storyboard_in_draft_for_retry(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    storyboard = await service.get_or_create_storyboard(episode_id, 1, 1)
    await session.commit()

    asset = await service.upload_keyframe(storyboard.id, "PROJ_1", b"bad take")
    await session.commit()
    rejected = await service.reject_keyframe(asset.id, "face drift")
    await session.commit()
    assert rejected.status.value == "rejected"

    still_draft = await service.get(storyboard.id)
    assert still_draft.status == "draft"

    retry = await service.upload_keyframe(storyboard.id, "PROJ_1", b"better take")
    await session.commit()
    assert retry.take_number == 2


async def test_list_keyframes_returns_lineage_in_order(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    storyboard = await service.get_or_create_storyboard(episode_id, 1, 1)
    await session.commit()

    await service.upload_keyframe(storyboard.id, "PROJ_1", b"take 1")
    await session.commit()
    await service.upload_keyframe(storyboard.id, "PROJ_1", b"take 2")
    await session.commit()

    keyframes = await service.list_keyframes("PROJ_1", storyboard)
    assert [k.take_number for k in keyframes] == [1, 2]


async def test_edit_keyframe_produces_new_take_referencing_base(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    storyboard = await service.get_or_create_storyboard(episode_id, 1, 1)
    await session.commit()

    base = await service.upload_keyframe(storyboard.id, "PROJ_1", b"original take")
    await session.commit()
    await service.accept_keyframe(storyboard.id, base.id)
    await session.commit()

    provider = FakeImageProvider(
        [b"edited take"], capabilities=ImageProviderCapabilities(supports_edit=True)
    )
    router = MediaProviderRouter([provider])
    edited = await service.edit_keyframe(storyboard.id, "PROJ_1", "fix the left hand", base.id, router)
    await session.commit()

    assert edited.take_number == 2
    assert edited.provenance.generation_params["edit"] is True
    assert edited.provenance.generation_params["based_on_take"] == base.id
    assert edited.provenance.source_reference_asset_ids == [base.id]
    assert await storage.read_bytes(edited.storage_path) == b"edited take"

    # The base take is untouched - never silently overwritten.
    still_base = await service.get(storyboard.id)
    assert still_base.approved_keyframe_asset_id == base.id
    assert await storage.read_bytes(base.storage_path) == b"original take"


async def test_edit_keyframe_includes_mask_in_lineage(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    storyboard = await service.get_or_create_storyboard(episode_id, 1, 1)
    await session.commit()
    base = await service.upload_keyframe(storyboard.id, "PROJ_1", b"base")
    mask = await service.upload_keyframe(storyboard.id, "PROJ_1", b"mask bytes")
    await session.commit()

    provider = FakeImageProvider(
        [b"masked edit"],
        capabilities=ImageProviderCapabilities(supports_edit=True, supports_mask=True),
    )
    router = MediaProviderRouter([provider])
    edited = await service.edit_keyframe(
        storyboard.id, "PROJ_1", "change wardrobe", base.id, router, mask_asset_id=mask.id
    )
    await session.commit()

    assert edited.provenance.source_reference_asset_ids == [base.id, mask.id]
    assert provider.edit_calls[0][1] is True  # mask was passed through


async def test_edit_keyframe_rejects_provider_without_edit_support(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    storyboard = await service.get_or_create_storyboard(episode_id, 1, 1)
    await session.commit()
    base = await service.upload_keyframe(storyboard.id, "PROJ_1", b"base")
    await session.commit()

    provider = FakeImageProvider(capabilities=ImageProviderCapabilities(supports_edit=False))
    router = MediaProviderRouter([provider])
    with pytest.raises(NoEligibleProviderError):
        await service.edit_keyframe(storyboard.id, "PROJ_1", "fix it", base.id, router)
    assert provider.edit_calls == []


async def test_edit_keyframe_rejects_mask_when_provider_lacks_mask_support(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    storyboard = await service.get_or_create_storyboard(episode_id, 1, 1)
    await session.commit()
    base = await service.upload_keyframe(storyboard.id, "PROJ_1", b"base")
    mask = await service.upload_keyframe(storyboard.id, "PROJ_1", b"mask")
    await session.commit()

    provider = FakeImageProvider(
        capabilities=ImageProviderCapabilities(supports_edit=True, supports_mask=False)
    )
    router = MediaProviderRouter([provider])
    with pytest.raises(NoEligibleProviderError):
        await service.edit_keyframe(
            storyboard.id, "PROJ_1", "fix it", base.id, router, mask_asset_id=mask.id
        )
