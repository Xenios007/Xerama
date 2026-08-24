"""FastAPI dependency wiring. Keeps routers free of SQLAlchemy/provider
construction details - see `app.py` lifespan for where the singletons
(engine, session factory, AI gateway) actually get built."""

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from xerama.pipeline.ai_gateway import AIGateway
from xerama.pipeline.episode_engine import EpisodeEngine
from xerama.pipeline.orchestrator import Showrunner
from xerama.providers.frame_extractor import FrameExtractor
from xerama.providers.image import ImageProvider
from xerama.providers.local_storage import LocalStorageProvider
from xerama.providers.video import VideoProvider
from xerama.services.media_router import MediaProviderRouter
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyAssetRepository,
    SQLAlchemyCharacterCastingRepository,
    SQLAlchemyConceptRepository,
    SQLAlchemyEpisodeRepository,
    SQLAlchemyJobRepository,
    SQLAlchemyProjectRepository,
    SQLAlchemySeasonRepository,
    SQLAlchemySeriesRepository,
    SQLAlchemyStoryboardRepository,
    SQLAlchemyStyleBibleRepository,
    SQLAlchemyVideoProductionRepository,
)
from xerama.services.asset_service import AssetService
from xerama.services.character_casting_service import CharacterCastingService
from xerama.services.storyboard_service import StoryboardService
from xerama.services.style_bible_service import StyleBibleService
from xerama.services.video_production_service import VideoProductionService


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


def get_storyboard_service(
    session: AsyncSession = Depends(get_session),
    storage: LocalStorageProvider = Depends(get_storage_provider),
) -> StoryboardService:
    return StoryboardService(
        storyboard_repo=SQLAlchemyStoryboardRepository(session),
        asset_service=AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session)),
    )


def get_image_router(request: Request) -> MediaProviderRouter[ImageProvider]:
    return request.app.state.image_router


def get_video_router(request: Request) -> MediaProviderRouter[VideoProvider]:
    return request.app.state.video_router


def get_frame_extractor(request: Request) -> FrameExtractor:
    return request.app.state.frame_extractor


def get_video_production_service(
    session: AsyncSession = Depends(get_session),
    storage: LocalStorageProvider = Depends(get_storage_provider),
    frame_extractor: FrameExtractor = Depends(get_frame_extractor),
) -> VideoProductionService:
    return VideoProductionService(
        production_repo=SQLAlchemyVideoProductionRepository(session),
        asset_service=AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session)),
        frame_extractor=frame_extractor,
    )


def get_project_repo(session: AsyncSession = Depends(get_session)) -> SQLAlchemyProjectRepository:
    return SQLAlchemyProjectRepository(session)


def get_series_repo(session: AsyncSession = Depends(get_session)) -> SQLAlchemySeriesRepository:
    return SQLAlchemySeriesRepository(session)


def get_episode_repo(session: AsyncSession = Depends(get_session)) -> SQLAlchemyEpisodeRepository:
    return SQLAlchemyEpisodeRepository(session)


def get_job_repo(session: AsyncSession = Depends(get_session)) -> SQLAlchemyJobRepository:
    return SQLAlchemyJobRepository(session)


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
