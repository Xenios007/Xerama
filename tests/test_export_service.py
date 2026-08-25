import pytest

from xerama.domain.enums import QCStatus
from xerama.domain.export import ExportProfile, MediaProbeResult
from xerama.providers.fake_assembler import FakeAssembler
from xerama.providers.fake_media_inspector import FakeMediaInspector
from xerama.providers.local_storage import LocalStorageProvider
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyAssetRepository,
    SQLAlchemyAudioProductionRepository,
    SQLAlchemyEpisodeRenderRepository,
    SQLAlchemyEpisodeRepository,
    SQLAlchemyMusicCueRepository,
    SQLAlchemySoundEffectCueRepository,
    SQLAlchemySubtitleCueRepository,
    SQLAlchemyVideoProductionRepository,
)
from xerama.services.assembly_service import EpisodeAssemblyService
from xerama.services.asset_service import AssetService
from xerama.services.export_service import VerticalExportService

from test_assembly_service import _approve_video_take, _episode_setup, _shot_plan


@pytest.fixture
def storage(tmp_path):
    return LocalStorageProvider(tmp_path / "store")


def _assembly_service(session, storage, assembler=None) -> EpisodeAssemblyService:
    return EpisodeAssemblyService(
        episode_repo=SQLAlchemyEpisodeRepository(session),
        video_production_repo=SQLAlchemyVideoProductionRepository(session),
        audio_production_repo=SQLAlchemyAudioProductionRepository(session),
        music_cue_repo=SQLAlchemyMusicCueRepository(session),
        sfx_cue_repo=SQLAlchemySoundEffectCueRepository(session),
        subtitle_repo=SQLAlchemySubtitleCueRepository(session),
        render_repo=SQLAlchemyEpisodeRenderRepository(session),
        asset_service=AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session)),
        assembler=assembler or FakeAssembler(),
    )


def _export_service(session, storage, assembler=None, inspector=None) -> VerticalExportService:
    return VerticalExportService(
        assembly_service=_assembly_service(session, storage, assembler),
        asset_service=AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session)),
        subtitle_repo=SQLAlchemySubtitleCueRepository(session),
        inspector=inspector or FakeMediaInspector(),
    )


async def test_export_episode_renders_and_validates(session, storage) -> None:
    project_id, series_id, episode_id = await _episode_setup(session)
    await SQLAlchemyEpisodeRepository(session).save_shot_plan(episode_id, _shot_plan())
    await session.commit()
    await _approve_video_take(session, storage, episode_id)

    service = _export_service(session, storage)
    asset, render, report = await service.export_episode(episode_id, project_id, series_id=series_id)
    await session.commit()

    assert asset.type.value == "video"
    assert render.version == 1
    assert report.status == QCStatus.WARN  # fake probe can't measure real duration/resolution


async def test_export_episode_uses_profile_output_spec(session, storage) -> None:
    project_id, series_id, episode_id = await _episode_setup(session)
    await SQLAlchemyEpisodeRepository(session).save_shot_plan(episode_id, _shot_plan())
    await session.commit()
    await _approve_video_take(session, storage, episode_id)

    assembler = FakeAssembler()
    service = _export_service(session, storage, assembler=assembler)
    profile = ExportProfile(name="mobile_720", output={"width": 720, "height": 1280, "fps": 24})
    await service.export_episode(episode_id, project_id, series_id=series_id, profile=profile)
    await session.commit()

    assert assembler.calls[0].output.width == 720
    assert assembler.calls[0].output.fps == 24


async def test_export_episode_blocks_on_corrupt_probe(session, storage) -> None:
    project_id, series_id, episode_id = await _episode_setup(session)
    await SQLAlchemyEpisodeRepository(session).save_shot_plan(episode_id, _shot_plan())
    await session.commit()
    await _approve_video_take(session, storage, episode_id)

    inspector = FakeMediaInspector([MediaProbeResult(ok=False, error="moov atom not found")])
    service = _export_service(session, storage, inspector=inspector)
    _, _, report = await service.export_episode(episode_id, project_id, series_id=series_id)
    await session.commit()

    assert report.status == QCStatus.BLOCK
