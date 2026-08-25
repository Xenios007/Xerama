import pytest

from xerama.domain.enums import AudioMode
from xerama.providers.fake_media_qc import FakeMediaQCProvider
from xerama.providers.fake_voice import FakeVoiceProvider
from xerama.providers.local_storage import LocalStorageProvider
from xerama.providers.voice import VoiceProviderCapabilities
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyAssetRepository,
    SQLAlchemyAudioProductionRepository,
    SQLAlchemyMediaQCRepository,
    SQLAlchemyVoiceProfileRepository,
)
from xerama.services.asset_service import AssetService
from xerama.services.audio_production_service import AudioProductionService
from xerama.services.media_qc_service import MediaQCService
from xerama.services.media_router import MediaProviderRouter, NoEligibleProviderError

from test_storyboard_repository import _episode


@pytest.fixture
def storage(tmp_path):
    return LocalStorageProvider(tmp_path / "store")


def _media_qc(session, storage, provider=None) -> MediaQCService:
    return MediaQCService(
        repo=SQLAlchemyMediaQCRepository(session),
        asset_service=AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session)),
        provider=provider or FakeMediaQCProvider(),
    )


def _service(session, storage) -> AudioProductionService:
    return AudioProductionService(
        production_repo=SQLAlchemyAudioProductionRepository(session),
        voice_profile_repo=SQLAlchemyVoiceProfileRepository(session),
        asset_service=AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session)),
        media_qc=_media_qc(session, storage),
    )


async def test_generate_dialogue_take_ingests_asset_with_lineage(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    production = await service.get_or_create_production(episode_id, 1, 1, AudioMode.TTS_LIPSYNC)
    await session.commit()

    voice_repo = SQLAlchemyVoiceProfileRepository(session)
    await voice_repo.save(
        (await voice_repo.get_or_create("CHAR_001")).model_copy(update={"provider_voice_id": "v-mara"})
    )
    await session.commit()

    provider = FakeVoiceProvider([b"synthesized line"])
    router = MediaProviderRouter([provider])
    asset = await service.generate_dialogue_take(
        production.id, "PROJ_1", "CHAR_001", "This can't be real.", router
    )
    await session.commit()

    assert asset.take_number == 1
    assert asset.status.value == "pending"
    assert asset.provenance.generation_params["character_id"] == "CHAR_001"
    assert asset.provenance.generation_params["audio_mode"] == "tts_lipsync"
    assert await storage.read_bytes(asset.storage_path) == b"synthesized line"
    assert provider.calls[0].voice_id == "v-mara"


async def test_generate_dialogue_take_numbers_increment_on_retry(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    production = await service.get_or_create_production(episode_id, 1, 1, AudioMode.TTS_LIPSYNC)
    await session.commit()

    provider = FakeVoiceProvider([b"take-1", b"take-2"])
    router = MediaProviderRouter([provider])
    first = await service.generate_dialogue_take(production.id, "PROJ_1", "CHAR_001", "Line one.", router)
    await session.commit()
    second = await service.generate_dialogue_take(production.id, "PROJ_1", "CHAR_001", "Line one retry.", router)
    await session.commit()

    assert first.take_number == 1
    assert second.take_number == 2


async def test_generate_dialogue_take_rejects_unsupported_language(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    production = await service.get_or_create_production(episode_id, 1, 1, AudioMode.TTS_LIPSYNC)
    await session.commit()

    voice_repo = SQLAlchemyVoiceProfileRepository(session)
    profile = await voice_repo.get_or_create("CHAR_001")
    profile.language = "fr"
    await voice_repo.save(profile)
    await session.commit()

    provider = FakeVoiceProvider(capabilities=VoiceProviderCapabilities(languages=["en"]))
    router = MediaProviderRouter([provider])
    with pytest.raises(NoEligibleProviderError):
        await service.generate_dialogue_take(production.id, "PROJ_1", "CHAR_001", "Bonjour.", router)
    assert provider.calls == []


async def test_generate_dialogue_take_rejects_text_over_max_characters(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    production = await service.get_or_create_production(episode_id, 1, 1, AudioMode.TTS_LIPSYNC)
    await session.commit()

    provider = FakeVoiceProvider(capabilities=VoiceProviderCapabilities(max_characters=5))
    router = MediaProviderRouter([provider])
    with pytest.raises(NoEligibleProviderError):
        await service.generate_dialogue_take(
            production.id, "PROJ_1", "CHAR_001", "this line is way too long", router
        )


async def test_reject_take_leaves_production_in_draft_for_retry(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    production = await service.get_or_create_production(episode_id, 1, 1, AudioMode.TTS_LIPSYNC)
    await session.commit()

    asset = await service.upload_dialogue_take(production.id, "PROJ_1", b"bad take")
    await session.commit()
    rejected = await service.reject_take(asset.id, "mispronounced name")
    await session.commit()
    assert rejected.status.value == "rejected"

    still_draft = await service.get(production.id)
    assert still_draft.status == "draft"

    retry = await service.upload_dialogue_take(production.id, "PROJ_1", b"better take")
    await session.commit()
    assert retry.take_number == 2


async def test_accept_take_marks_production_approved(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    production = await service.get_or_create_production(episode_id, 1, 1, AudioMode.TTS_LIPSYNC)
    await session.commit()

    asset = await service.upload_dialogue_take(production.id, "PROJ_1", b"data")
    await session.commit()
    approved = await service.accept_take(production.id, asset.id)
    await session.commit()

    assert approved.status == "approved"
    assert approved.approved_take_asset_id == asset.id


async def test_accept_take_blocked_by_negative_duration(session, storage) -> None:
    """MODULE-044 - `check_dialogue_audio` BLOCKs a genuinely impossible
    (negative) measured duration, keeping the take not-accepted."""
    from xerama.domain.enums import QCStatus
    from xerama.services.media_qc_service import QCGateBlockedError

    episode_id = await _episode(session)
    service = _service(session, storage)
    production = await service.get_or_create_production(episode_id, 1, 1, AudioMode.TTS_LIPSYNC)
    await session.commit()

    asset_service = AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session))
    from xerama.domain.asset import AssetOwnership, AssetType

    asset = await asset_service.ingest_bytes(
        b"data",
        AssetType.AUDIO,
        AssetOwnership(project_id="PROJ_1", episode_id=episode_id, scene_number=1, shot_number=1),
        duration_seconds=-1.0,
    )
    await session.commit()

    with pytest.raises(QCGateBlockedError):
        await service.accept_take(production.id, asset.id)
    await session.commit()

    unchanged = await service.get(production.id)
    assert unchanged.status == "draft"


async def test_list_takes_returns_lineage_in_order(session, storage) -> None:
    episode_id = await _episode(session)
    service = _service(session, storage)
    production = await service.get_or_create_production(episode_id, 1, 1, AudioMode.TTS_LIPSYNC)
    await session.commit()

    await service.upload_dialogue_take(production.id, "PROJ_1", b"take 1")
    await session.commit()
    await service.upload_dialogue_take(production.id, "PROJ_1", b"take 2")
    await session.commit()

    takes = await service.list_takes("PROJ_1", production)
    assert [t.take_number for t in takes] == [1, 2]


async def test_generate_with_auto_heal_repairs_after_media_health_block(session, storage) -> None:
    """MODULE-045 - a genuine MEDIA_HEALTH BLOCK (zero-byte take from a
    misbehaving provider) triggers an ALTERNATE_PROVIDER retry that
    excludes the failing provider and succeeds on the next one."""
    from xerama.services.retake_service import AutomaticRetakeService

    episode_id = await _episode(session)
    service = _service(session, storage)
    production = await service.get_or_create_production(episode_id, 1, 1, AudioMode.TTS_LIPSYNC)
    await session.commit()

    flaky = FakeVoiceProvider([b""], name="flaky")
    reliable = FakeVoiceProvider([b"good audio"], name="reliable")
    router = MediaProviderRouter([flaky, reliable])
    asset, approved = await service.generate_with_auto_heal(
        production.id, "PROJ_1", "CHAR_001", "This can't be real.", router, AutomaticRetakeService()
    )
    await session.commit()

    assert asset.take_number == 2
    assert asset.provenance.provider == "reliable"
    assert approved.status == "approved"
    assert approved.auto_retake_attempts == 1

    takes = await service.list_takes("PROJ_1", production)
    rejected = [t for t in takes if t.take_number == 1]
    assert rejected[0].status.value == "rejected"
    assert "zero size_bytes" in rejected[0].rejection_reason
