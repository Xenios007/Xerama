"""FastAPI application factory. See README.md "First end-to-end test"."""

import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from xerama.api.middleware import correlation_id_middleware
from xerama.api.routers import (
    analytics,
    assembly,
    assets,
    audio_production,
    auth,
    characters,
    costs,
    episodes,
    feedback,
    generation,
    health,
    inspect,
    jobs,
    music_cues,
    optimization,
    projects,
    season,
    sound_effect_cues,
    storyboards,
    style_bible,
    subtitles,
    video_production,
    voice_profile,
)
from xerama.config import ModelRoleRegistry, Settings, get_settings
from xerama.db.base import create_all, make_engine, make_session_factory
from xerama.observability.logging import configure_structured_logging
from xerama.pipeline.ai_gateway import AIGateway
from xerama.providers.fake_assembler import FakeAssembler
from xerama.providers.fake_frame_extractor import FakeFrameExtractor
from xerama.providers.fake_image import FakeImageProvider
from xerama.providers.fake_lip_sync import FakeLipSyncProvider
from xerama.providers.fake_media_inspector import FakeMediaInspector
from xerama.providers.fake_media_qc import FakeMediaQCProvider
from xerama.providers.fake_video import FakeVideoProvider
from xerama.providers.fake_voice import FakeVoiceProvider
from xerama.providers.ffmpeg_assembler import FFmpegAssembler, ffmpeg_is_available
from xerama.providers.ffmpeg_frame_extractor import FFmpegFrameExtractor
from xerama.providers.ffprobe_inspector import FFprobeInspector
from xerama.providers.health import ProviderHealthTracker
from xerama.providers.local_storage import LocalStorageProvider
from xerama.providers.openrouter import OpenRouterProvider
from xerama.services.media_router import MediaProviderRouter


def _configure_logging(settings: Settings) -> None:
    configure_structured_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    _configure_logging(settings)

    engine = make_engine(settings.database_url)
    await create_all(engine)
    session_factory = make_session_factory(engine)

    http_client = httpx.AsyncClient(timeout=120.0)
    provider = OpenRouterProvider(
        api_key=settings.openrouter_api_key.get_secret_value(),
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
    # MODULE-044 - no real vision-capable QC model is wired up yet either;
    # the fake gives every accept_* call a real (structurally-enforced) QC
    # gate to pass through today, ready to swap for a real scorer later.
    app.state.media_qc_provider = FakeMediaQCProvider()
    # Real last-frame extraction needs an `ffmpeg` binary on PATH - fall
    # back to the fake extractor (still a fully working no-video-decode
    # placeholder) when one isn't installed, same "optional real adapter"
    # principle as every media provider above.
    app.state.frame_extractor = (
        FFmpegFrameExtractor(ffmpeg_path=settings.ffmpeg_path)
        if shutil.which(settings.ffmpeg_path)
        else FakeFrameExtractor()
    )
    # MODULE-046 - same "optional real adapter" principle: a real FFmpeg
    # assembly pipeline when the binary is available, a deterministic
    # placeholder otherwise, both behind the same `EpisodeAssembler`
    # Protocol so no caller code branches on which one is active.
    app.state.episode_assembler = (
        FFmpegAssembler(ffmpeg_path=settings.ffmpeg_path)
        if ffmpeg_is_available(settings.ffmpeg_path)
        else FakeAssembler()
    )
    # MODULE-048 - same principle, one more optional real adapter.
    app.state.media_inspector = (
        FFprobeInspector(ffprobe_path=settings.ffprobe_path)
        if shutil.which(settings.ffprobe_path)
        else FakeMediaInspector()
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
    app.middleware("http")(correlation_id_middleware)
    settings = get_settings()
    allowed_origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(projects.router)
    app.include_router(generation.router)
    # jobs.router must be registered before inspect.router - inspect.py's
    # GET /jobs/{job_id} would otherwise shadow jobs.py's static
    # /jobs/queued and /jobs/failed paths (Starlette matches routes in
    # registration order).
    app.include_router(jobs.router)
    app.include_router(inspect.router)
    app.include_router(season.router)
    app.include_router(episodes.router)
    app.include_router(assets.router)
    app.include_router(characters.router)
    app.include_router(style_bible.router)
    app.include_router(storyboards.router)
    app.include_router(video_production.router)
    app.include_router(voice_profile.router)
    app.include_router(audio_production.router)
    app.include_router(music_cues.router)
    app.include_router(sound_effect_cues.router)
    app.include_router(subtitles.router)
    app.include_router(assembly.router)
    app.include_router(costs.router)
    app.include_router(analytics.router)
    app.include_router(optimization.router)
    app.include_router(feedback.router)
    return app


app = create_app()
