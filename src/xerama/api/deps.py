"""FastAPI dependency wiring. Keeps routers free of SQLAlchemy/provider
construction details - see `app.py` lifespan for where the singletons
(engine, session factory, AI gateway) actually get built."""

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from xerama.pipeline.ai_gateway import AIGateway
from xerama.pipeline.episode_engine import EpisodeEngine
from xerama.pipeline.orchestrator import Showrunner
from xerama.providers.assembler import EpisodeAssembler
from xerama.providers.frame_extractor import FrameExtractor
from xerama.providers.media_inspector import MediaInspector
from xerama.providers.image import ImageProvider
from xerama.providers.lip_sync import LipSyncProvider
from xerama.providers.local_storage import LocalStorageProvider
from xerama.providers.media_qc import MediaQCProvider
from xerama.providers.video import VideoProvider
from xerama.providers.voice import VoiceProvider
from xerama.services.media_router import MediaProviderRouter
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyAssetRepository,
    SQLAlchemyAudioProductionRepository,
    SQLAlchemyCharacterCastingRepository,
    SQLAlchemyConceptRepository,
    SQLAlchemyCostRecordRepository,
    SQLAlchemyEpisodeRenderRepository,
    SQLAlchemyEpisodeRepository,
    SQLAlchemyJobRepository,
    SQLAlchemyMediaQCRepository,
    SQLAlchemyMusicCueRepository,
    SQLAlchemyProjectRepository,
    SQLAlchemySeasonRepository,
    SQLAlchemySeriesRepository,
    SQLAlchemySoundEffectCueRepository,
    SQLAlchemyStoryboardRepository,
    SQLAlchemyStyleBibleRepository,
    SQLAlchemySubtitleCueRepository,
    SQLAlchemyVideoProductionRepository,
    SQLAlchemyVoiceProfileRepository,
)
from xerama.services.assembly_service import EpisodeAssemblyService
from xerama.services.asset_service import AssetService
from xerama.services.audio_production_service import AudioProductionService
from xerama.services.character_casting_service import CharacterCastingService
from xerama.services.cost_service import CostRecordService
from xerama.services.export_service import VerticalExportService
from xerama.services.observability_service import ObservabilityService
from xerama.services.media_qc_service import MediaQCService
from xerama.services.music_cue_service import MusicCueService
from xerama.services.retake_service import AutomaticRetakeService
from xerama.services.sound_effect_service import SoundEffectCueService
from xerama.services.storyboard_service import StoryboardService
from xerama.services.style_bible_service import StyleBibleService
from xerama.services.subtitle_service import SubtitleService
from xerama.services.video_production_service import VideoProductionService
from xerama.services.voice_profile_service import VoiceProfileService


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_gateway(request: Request) -> AIGateway:
    return request.app.state.ai_gateway


def get_storage_provider(request: Request) -> LocalStorageProvider:
    return request.app.state.storage_provider


def get_asset_service(
    session: AsyncSession = Depends(get_session),
    storage: LocalStorageProvider = Depends(get_storage_provider),
) -> AssetService:
    return AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session))


def get_character_casting_service(
    session: AsyncSession = Depends(get_session),
) -> CharacterCastingService:
    return CharacterCastingService(repo=SQLAlchemyCharacterCastingRepository(session))


def get_style_bible_repo(session: AsyncSession = Depends(get_session)) -> SQLAlchemyStyleBibleRepository:
    return SQLAlchemyStyleBibleRepository(session)


def get_style_bible_service(
    session: AsyncSession = Depends(get_session),
) -> StyleBibleService:
    return StyleBibleService(repo=SQLAlchemyStyleBibleRepository(session))


def get_retake_service() -> AutomaticRetakeService:
    return AutomaticRetakeService()


def get_cost_service(session: AsyncSession = Depends(get_session)) -> CostRecordService:
    return CostRecordService(repo=SQLAlchemyCostRecordRepository(session))


def get_observability_service(
    session: AsyncSession = Depends(get_session),
    cost_service: CostRecordService = Depends(get_cost_service),
) -> ObservabilityService:
    return ObservabilityService(job_repo=SQLAlchemyJobRepository(session), cost_service=cost_service)


def get_media_qc_provider(request: Request) -> MediaQCProvider:
    return request.app.state.media_qc_provider


def get_media_qc_service(
    session: AsyncSession = Depends(get_session),
    storage: LocalStorageProvider = Depends(get_storage_provider),
    provider: MediaQCProvider = Depends(get_media_qc_provider),
) -> MediaQCService:
    return MediaQCService(
        repo=SQLAlchemyMediaQCRepository(session),
        asset_service=AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session)),
        provider=provider,
    )


def get_storyboard_service(
    session: AsyncSession = Depends(get_session),
    storage: LocalStorageProvider = Depends(get_storage_provider),
    media_qc: MediaQCService = Depends(get_media_qc_service),
) -> StoryboardService:
    return StoryboardService(
        storyboard_repo=SQLAlchemyStoryboardRepository(session),
        asset_service=AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session)),
        media_qc=media_qc,
    )


def get_image_router(request: Request) -> MediaProviderRouter[ImageProvider]:
    return request.app.state.image_router


def get_video_router(request: Request) -> MediaProviderRouter[VideoProvider]:
    return request.app.state.video_router


def get_lip_sync_router(request: Request) -> MediaProviderRouter[LipSyncProvider]:
    return request.app.state.lip_sync_router


def get_frame_extractor(request: Request) -> FrameExtractor:
    return request.app.state.frame_extractor


def get_video_production_service(
    session: AsyncSession = Depends(get_session),
    storage: LocalStorageProvider = Depends(get_storage_provider),
    frame_extractor: FrameExtractor = Depends(get_frame_extractor),
    media_qc: MediaQCService = Depends(get_media_qc_service),
) -> VideoProductionService:
    return VideoProductionService(
        production_repo=SQLAlchemyVideoProductionRepository(session),
        asset_service=AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session)),
        frame_extractor=frame_extractor,
        media_qc=media_qc,
    )


def get_voice_profile_repo(
    session: AsyncSession = Depends(get_session),
) -> SQLAlchemyVoiceProfileRepository:
    return SQLAlchemyVoiceProfileRepository(session)


def get_voice_profile_service(
    session: AsyncSession = Depends(get_session),
) -> VoiceProfileService:
    return VoiceProfileService(repo=SQLAlchemyVoiceProfileRepository(session))


def get_voice_router(request: Request) -> MediaProviderRouter[VoiceProvider]:
    return request.app.state.voice_router


def get_audio_production_service(
    session: AsyncSession = Depends(get_session),
    storage: LocalStorageProvider = Depends(get_storage_provider),
    media_qc: MediaQCService = Depends(get_media_qc_service),
) -> AudioProductionService:
    return AudioProductionService(
        production_repo=SQLAlchemyAudioProductionRepository(session),
        voice_profile_repo=SQLAlchemyVoiceProfileRepository(session),
        asset_service=AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session)),
        media_qc=media_qc,
    )


def get_music_cue_service(session: AsyncSession = Depends(get_session)) -> MusicCueService:
    return MusicCueService(repo=SQLAlchemyMusicCueRepository(session))


def get_sound_effect_cue_service(
    session: AsyncSession = Depends(get_session),
) -> SoundEffectCueService:
    return SoundEffectCueService(repo=SQLAlchemySoundEffectCueRepository(session))


def get_subtitle_service(session: AsyncSession = Depends(get_session)) -> SubtitleService:
    return SubtitleService(repo=SQLAlchemySubtitleCueRepository(session))


def get_episode_assembler(request: Request) -> EpisodeAssembler:
    return request.app.state.episode_assembler


def get_assembly_service(
    session: AsyncSession = Depends(get_session),
    storage: LocalStorageProvider = Depends(get_storage_provider),
    assembler: EpisodeAssembler = Depends(get_episode_assembler),
) -> EpisodeAssemblyService:
    return EpisodeAssemblyService(
        episode_repo=SQLAlchemyEpisodeRepository(session),
        video_production_repo=SQLAlchemyVideoProductionRepository(session),
        audio_production_repo=SQLAlchemyAudioProductionRepository(session),
        music_cue_repo=SQLAlchemyMusicCueRepository(session),
        sfx_cue_repo=SQLAlchemySoundEffectCueRepository(session),
        subtitle_repo=SQLAlchemySubtitleCueRepository(session),
        render_repo=SQLAlchemyEpisodeRenderRepository(session),
        asset_service=AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session)),
        assembler=assembler,
    )


def get_media_inspector(request: Request) -> MediaInspector:
    return request.app.state.media_inspector


def get_export_service(
    session: AsyncSession = Depends(get_session),
    storage: LocalStorageProvider = Depends(get_storage_provider),
    assembly_service: EpisodeAssemblyService = Depends(get_assembly_service),
    inspector: MediaInspector = Depends(get_media_inspector),
) -> VerticalExportService:
    return VerticalExportService(
        assembly_service=assembly_service,
        asset_service=AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session)),
        subtitle_repo=SQLAlchemySubtitleCueRepository(session),
        inspector=inspector,
    )


def get_project_repo(session: AsyncSession = Depends(get_session)) -> SQLAlchemyProjectRepository:
    return SQLAlchemyProjectRepository(session)


def get_concept_repo(session: AsyncSession = Depends(get_session)) -> SQLAlchemyConceptRepository:
    return SQLAlchemyConceptRepository(session)


def get_series_repo(session: AsyncSession = Depends(get_session)) -> SQLAlchemySeriesRepository:
    return SQLAlchemySeriesRepository(session)


def get_episode_repo(session: AsyncSession = Depends(get_session)) -> SQLAlchemyEpisodeRepository:
    return SQLAlchemyEpisodeRepository(session)


def get_job_repo(session: AsyncSession = Depends(get_session)) -> SQLAlchemyJobRepository:
    return SQLAlchemyJobRepository(session)


def get_episode_render_repo(
    session: AsyncSession = Depends(get_session),
) -> SQLAlchemyEpisodeRenderRepository:
    return SQLAlchemyEpisodeRenderRepository(session)


def get_season_repo(session: AsyncSession = Depends(get_session)) -> SQLAlchemySeasonRepository:
    return SQLAlchemySeasonRepository(session)


def get_episode_engine(
    session: AsyncSession = Depends(get_session), gateway: AIGateway = Depends(get_gateway)
) -> EpisodeEngine:
    return EpisodeEngine(
        gateway=gateway,
        series_repo=SQLAlchemySeriesRepository(session),
        episode_repo=SQLAlchemyEpisodeRepository(session),
        job_repo=SQLAlchemyJobRepository(session),
    )


def get_showrunner(
    session: AsyncSession = Depends(get_session), gateway: AIGateway = Depends(get_gateway)
) -> Showrunner:
    return Showrunner(
        gateway=gateway,
        concept_repo=SQLAlchemyConceptRepository(session),
        series_repo=SQLAlchemySeriesRepository(session),
        season_repo=SQLAlchemySeasonRepository(session),
        episode_repo=SQLAlchemyEpisodeRepository(session),
        job_repo=SQLAlchemyJobRepository(session),
    )
