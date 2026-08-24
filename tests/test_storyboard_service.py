import pytest

from xerama.domain.generation_request import CompiledReferences, ShotGenerationRequest
from xerama.domain.scene import Camera, ProviderRequirements, Visual
from xerama.domain.enums import AudioMode
from xerama.providers.fake_image import FakeImageProvider
from xerama.providers.image import ImageProviderCapabilities
from xerama.providers.local_storage import LocalStorageProvider
from xerama.repositories.sqlalchemy_impl import SQLAlchemyAssetRepository, SQLAlchemyStoryboardRepository
from xerama.services.asset_service import AssetService
from xerama.services.storyboard_service import StoryboardService, UnsupportedProviderCapabilityError

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
    asset = await service.generate_keyframe(storyboard.id, "PROJ_1", _request(), provider)
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
    first = await service.generate_keyframe(storyboard.id, "PROJ_1", _request(), provider)
    await session.commit()
    second = await service.generate_keyframe(storyboard.id, "PROJ_1", _request(), provider)
    await session.commit()

    assert first.take_number == 1
    assert second.take_number == 2


async def test_generate_keyframe_rejects_unsupported_aspect_ratio(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    storyboard = await service.get_or_create_storyboard(episode_id, 1, 1)
    await session.commit()

    provider = FakeImageProvider(capabilities=ImageProviderCapabilities(supported_aspects=["16:9"]))
    with pytest.raises(UnsupportedProviderCapabilityError):
        await service.generate_keyframe(storyboard.id, "PROJ_1", _request(aspect_ratio="9:16"), provider)
    assert provider.calls == []  # rejected before spending a generation request


async def test_generate_keyframe_rejects_when_references_unsupported(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    storyboard = await service.get_or_create_storyboard(episode_id, 1, 1)
    await session.commit()

    provider = FakeImageProvider(capabilities=ImageProviderCapabilities(supports_reference_images=False))
    request = _request(references=CompiledReferences(character_asset_ids=["CHAR_001"]))
    with pytest.raises(UnsupportedProviderCapabilityError):
        await service.generate_keyframe(storyboard.id, "PROJ_1", request, provider)


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
