import pytest

from xerama.domain.enums import AudioMode
from xerama.domain.generation_request import CompiledReferences, ShotGenerationRequest
from xerama.domain.scene import Camera, ProviderRequirements, Visual
from xerama.providers.fake_frame_extractor import FakeFrameExtractor
from xerama.providers.fake_video import FakeVideoProvider
from xerama.providers.local_storage import LocalStorageProvider
from xerama.providers.video import VideoProviderCapabilities
from xerama.repositories.sqlalchemy_impl import SQLAlchemyAssetRepository, SQLAlchemyVideoProductionRepository
from xerama.services.asset_service import AssetService
from xerama.services.media_router import MediaProviderRouter, NoEligibleProviderError
from xerama.services.video_production_service import ContinuityOrderingError, VideoProductionService

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


@pytest.fixture
def storage(tmp_path):
    return LocalStorageProvider(tmp_path / "store")


def _service(session, storage, frame_extractor=None) -> VideoProductionService:
    return VideoProductionService(
        production_repo=SQLAlchemyVideoProductionRepository(session),
        asset_service=AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session)),
        frame_extractor=frame_extractor or FakeFrameExtractor(),
    )


async def test_generate_take_ingests_asset(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    production = await service.get_or_create_production(episode_id, 1, 1)
    await session.commit()

    provider = FakeVideoProvider([b"clip-take-1"])
    router = MediaProviderRouter([provider])
    asset = await service.generate_take(production.id, "PROJ_1", _request(), router)
    await session.commit()

    assert asset.take_number == 1
    assert asset.status.value == "pending"
    assert await storage.read_bytes(asset.storage_path) == b"clip-take-1"


async def test_generate_take_numbers_increment_on_retry(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    production = await service.get_or_create_production(episode_id, 1, 1)
    await session.commit()

    provider = FakeVideoProvider([b"take-1", b"take-2"])
    router = MediaProviderRouter([provider])
    first = await service.generate_take(production.id, "PROJ_1", _request(), router)
    await session.commit()
    second = await service.generate_take(production.id, "PROJ_1", _request(), router)
    await session.commit()

    assert first.take_number == 1
    assert second.take_number == 2


async def test_generate_take_rejects_incompatible_provider(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    production = await service.get_or_create_production(episode_id, 1, 1)
    await session.commit()

    provider = FakeVideoProvider(capabilities=VideoProviderCapabilities(supported_aspects=["16:9"]))
    router = MediaProviderRouter([provider])
    with pytest.raises(NoEligibleProviderError):
        await service.generate_take(production.id, "PROJ_1", _request(aspect_ratio="9:16"), router)
    assert provider.calls == []


async def test_standalone_shot_take_never_extracts_last_frame(session, storage) -> None:
    episode_id = await _episode(session)
    extractor = FakeFrameExtractor()
    service = _service(session, storage, frame_extractor=extractor)
    production = await service.get_or_create_production(episode_id, 1, 1)  # no continuity_group
    await session.commit()

    provider = FakeVideoProvider([b"clip"])
    router = MediaProviderRouter([provider])
    asset = await service.generate_take(production.id, "PROJ_1", _request(), router)
    await session.commit()

    accepted = await service.accept_take(production.id, asset.id)
    await session.commit()
    assert accepted.status == "approved"
    assert accepted.extracted_last_frame_asset_id is None
    assert extractor.calls == []  # standalone shots never trigger extraction


async def test_continuity_group_second_shot_requires_first_extracted(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    first = await service.get_or_create_production(episode_id, 1, 1, continuity_group="GRP_A")
    second = await service.get_or_create_production(episode_id, 1, 2, continuity_group="GRP_A")
    await session.commit()

    provider = FakeVideoProvider([b"clip-2"])
    router = MediaProviderRouter([provider])
    with pytest.raises(ContinuityOrderingError):
        await service.generate_take(second.id, "PROJ_1", _request(shot_number=2), router)
    assert provider.calls == []  # rejected before spending a generation request


async def test_continuity_group_chains_extracted_last_frame_into_next_shot(session, storage) -> None:
    episode_id = await _episode(session)
    extractor = FakeFrameExtractor()
    service = _service(session, storage, frame_extractor=extractor)
    first = await service.get_or_create_production(episode_id, 1, 1, continuity_group="GRP_A")
    second = await service.get_or_create_production(episode_id, 1, 2, continuity_group="GRP_A")
    await session.commit()

    provider = FakeVideoProvider([b"clip-1", b"clip-2"])
    router = MediaProviderRouter([provider])

    take1 = await service.generate_take(first.id, "PROJ_1", _request(), router)
    await session.commit()
    accepted_first = await service.accept_take(first.id, take1.id)
    await session.commit()
    assert accepted_first.extracted_last_frame_asset_id is not None
    assert extractor.calls == [b"clip-1"]

    # Resume behavior: generating the second shot in a later "session" works
    # now that its predecessor is accepted and extracted.
    take2 = await service.generate_take(second.id, "PROJ_1", _request(shot_number=2), router)
    await session.commit()
    assert take2.take_number == 1
    assert provider.calls[1][2] == b"fake-last-frame:clip-1"  # first_frame passed through


async def test_reject_take_leaves_production_in_draft_for_retry(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    production = await service.get_or_create_production(episode_id, 1, 1)
    await session.commit()

    asset = await service.upload_take(production.id, "PROJ_1", b"bad take")
    await session.commit()
    rejected = await service.reject_take(asset.id, "artifact glitch")
    await session.commit()
    assert rejected.status.value == "rejected"

    still_draft = await service.get(production.id)
    assert still_draft.status == "draft"

    retry = await service.upload_take(production.id, "PROJ_1", b"better take")
    await session.commit()
    assert retry.take_number == 2


async def test_list_takes_returns_lineage_in_order(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    production = await service.get_or_create_production(episode_id, 1, 1)
    await session.commit()

    await service.upload_take(production.id, "PROJ_1", b"take 1")
    await session.commit()
    await service.upload_take(production.id, "PROJ_1", b"take 2")
    await session.commit()

    takes = await service.list_takes("PROJ_1", production)
    assert [t.take_number for t in takes] == [1, 2]


async def test_upload_take_manual_fallback(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    production = await service.get_or_create_production(episode_id, 1, 1)
    await session.commit()

    asset = await service.upload_take(production.id, "PROJ_1", b"uploaded clip", mime_type="video/mp4")
    await session.commit()
    assert asset.provenance.provider == "manual_upload"
    assert asset.take_number == 1
