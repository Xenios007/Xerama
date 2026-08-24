"""FastAPI application factory. See README.md "First end-to-end test"."""

import logging
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from xerama.api.routers import (
    assets,
    characters,
    episodes,
    generation,
    inspect,
    projects,
    season,
    storyboards,
    style_bible,
    video_production,
)
from xerama.config import ModelRoleRegistry, Settings, get_settings
from xerama.db.base import create_all, make_engine, make_session_factory
from xerama.pipeline.ai_gateway import AIGateway
from xerama.providers.fake_frame_extractor import FakeFrameExtractor
from xerama.providers.fake_image import FakeImageProvider
from xerama.providers.fake_lip_sync import FakeLipSyncProvider
from xerama.providers.fake_video import FakeVideoProvider
from xerama.providers.fake_voice import FakeVoiceProvider
from xerama.providers.ffmpeg_frame_extractor import FFmpegFrameExtractor
from xerama.providers.health import ProviderHealthTracker
from xerama.providers.local_storage import LocalStorageProvider
from xerama.providers.openrouter import OpenRouterProvider
from xerama.services.media_router import MediaProviderRouter


def _configure_logging(settings: Settings) -> None:
    logging.basicConfig(level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    _configure_logging(settings)

    engine = make_engine(settings.database_url)
    await create_all(engine)
    session_factory = make_session_factory(engine)

    http_client = httpx.AsyncClient(timeout=120.0)
    provider = OpenRouterProvider(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        http_client=http_client,
    )
    gateway = AIGateway(
        provider=provider,
        roles=ModelRoleRegistry(settings),
        health=ProviderHealthTracker(),
    )

    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.ai_gateway = gateway
    app.state.http_client = http_client
    app.state.storage_provider = LocalStorageProvider(settings.asset_storage_path)
    # No free/trial media API is wired up yet for any of these - see
    # Module 06/07. Manual asset upload (Module 04) remains the first-class
    # fallback for images; video/voice/lip-sync consumers arrive in
    # Modules 08/09. Each registry can register additional real adapters
    # later without any caller-side change - they only ever ask a router
    # for a capability, never a vendor.
    app.state.image_router = MediaProviderRouter([FakeImageProvider()])
    app.state.video_router = MediaProviderRouter([FakeVideoProvider()])
    app.state.voice_router = MediaProviderRouter([FakeVoiceProvider()])
    app.state.lip_sync_router = MediaProviderRouter([FakeLipSyncProvider()])
    # Real last-frame extraction needs an `ffmpeg` binary on PATH - fall
    # back to the fake extractor (still a fully working no-video-decode
    # placeholder) when one isn't installed, same "optional real adapter"
    # principle as every media provider above.
    app.state.frame_extractor = (
        FFmpegFrameExtractor() if shutil.which("ffmpeg") else FakeFrameExtractor()
    )

    yield

    await http_client.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Xerama",
        description="AI microdrama production system - XER-001 story pipeline API.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(projects.router)
    app.include_router(generation.router)
    app.include_router(inspect.router)
    app.include_router(season.router)
    app.include_router(episodes.router)
    app.include_router(assets.router)
    app.include_router(characters.router)
    app.include_router(style_bible.router)
    app.include_router(storyboards.router)
    app.include_router(video_production.router)
    return app


app = create_app()
