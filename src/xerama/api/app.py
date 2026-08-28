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
    chat,
    characters,
    costs,
    episodes,
    eval,
    feedback,
    generation,
    health,
    inspect,
    jobs,
    media_eval,
    music_cues,
    optimization,
    projects,
    season,
    settings as settings_router,
    sound_effect_cues,
    storyboards,
    style_bible,
    subtitles,
    video_production,
    voice_profile,
)
from xerama.config import ROLE_MODEL_FIELDS, ModelRoleRegistry, Settings, get_settings
from xerama.db.base import create_all, make_engine, make_session_factory
from xerama.domain.runtime_settings import RuntimeSettings
from xerama.observability.logging import configure_structured_logging
from xerama.pipeline.ai_gateway import AIGateway
from xerama.pipeline.rate_limiting import RateLimiter
from xerama.repositories.sqlalchemy_impl import SQLAlchemyRuntimeSettingsRepository
from xerama.providers.fake_assembler import FakeAssembler
from xerama.providers.fake_frame_extractor import FakeFrameExtractor
from xerama.providers.fake_image import FakeImageProvider
from xerama.providers.fake_lip_sync import FakeLipSyncProvider
from xerama.providers.fake_media_inspector import FakeMediaInspector
from xerama.providers.fake_media_qc import FakeMediaQCProvider
from xerama.providers.fake_video import FakeVideoProvider
from xerama.providers.fal_image import FalImageProvider
from xerama.providers.fal_video import FalVideoProvider
from xerama.providers.video import VideoProviderCapabilities
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


def rebuild_providers(
    app: FastAPI,
    settings: Settings,
    runtime_settings: RuntimeSettings,
    http_client: httpx.AsyncClient,
) -> None:
    """(Re)builds the provider-dependent parts of app state from the
    current `RuntimeSettings` selection - called once at startup and again
    from `PATCH /settings` so a provider/model change takes effect
    immediately, no restart needed. Everything else in `app.state`
    (storage, rate limiter, ffmpeg-backed providers, voice/lip-sync) is
    independent of this choice and stays untouched."""
    if runtime_settings.llm_provider == "ollama":
        # A local model applies to every role uniformly (testing-phase
        # simplicity, not a limitation of the mechanism) - reuses
        # `ModelRoleRegistry.resolve()` (config.py) completely unchanged.
        effective_settings = settings.model_copy(
            update={field: runtime_settings.ollama_model for field in ROLE_MODEL_FIELDS}
        )
        llm_provider = OpenRouterProvider(
            api_key="ollama",  # ignored by Ollama's OpenAI-compat endpoint
            base_url=runtime_settings.ollama_base_url,
            http_client=http_client,
        )
    else:
        effective_settings = settings
        llm_provider = OpenRouterProvider(
            api_key=settings.openrouter_api_key.get_secret_value(),
            base_url=settings.openrouter_base_url,
            http_client=http_client,
        )
    app.state.ai_gateway = AIGateway(
        provider=llm_provider,
        roles=ModelRoleRegistry(effective_settings),
        health=ProviderHealthTracker(),
    )

    # Real image/video adapters (fal.ai) when both FAL_API_KEY is configured
    # AND the runtime setting selects "fal" - fake otherwise, same "fake now,
    # real adapter later" pattern as every other external provider. Voice/
    # lip-sync real adapters aren't built yet (Module 09), so those stay fake
    # regardless and aren't rebuilt here.
    fal_api_key = settings.fal_api_key.get_secret_value()
    if runtime_settings.media_provider == "fal" and fal_api_key:
        app.state.image_router = MediaProviderRouter(
            [FalImageProvider(api_key=fal_api_key, http_client=http_client)]
        )
        app.state.video_router = MediaProviderRouter(
            [FalVideoProvider(api_key=fal_api_key, http_client=http_client)]
        )
    else:
        app.state.image_router = MediaProviderRouter([FakeImageProvider()])
        # native_audio=True: several real 2026 video models (e.g. Veo/Sora-class)
        # generate audio natively, and the shot planner is free to request it -
        # the fake stand-in should cover that capability rather than reject it.
        app.state.video_router = MediaProviderRouter(
            [FakeVideoProvider(capabilities=VideoProviderCapabilities(native_audio=True))]
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    _configure_logging(settings)

    engine = make_engine(settings.database_url)
    await create_all(engine)
    session_factory = make_session_factory(engine)

    http_client = httpx.AsyncClient(timeout=120.0)

    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.http_client = http_client
    app.state.storage_provider = LocalStorageProvider(settings.asset_storage_path)
    # MODULE-068 - process-lifetime, in-memory (see rate_limiting.py's
    # docstring for why not DB-backed); permissive defaults so standard
    # mode is unaffected, tightened via env for hosted deployments.
    app.state.rate_limiter = RateLimiter(
        requests_per_window=settings.rate_limit_requests_per_window,
        window_seconds=settings.rate_limit_window_seconds,
        max_concurrent_per_project=settings.rate_limit_max_concurrent_per_project,
    )

    async with session_factory() as session:
        runtime_settings = await SQLAlchemyRuntimeSettingsRepository(session).get_or_create()
        await session.commit()
    rebuild_providers(app, settings, runtime_settings, http_client)

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
        FFmpegFrameExtractor(
            ffmpeg_path=settings.ffmpeg_path, timeout_seconds=settings.ffmpeg_timeout_seconds
        )
        if shutil.which(settings.ffmpeg_path)
        else FakeFrameExtractor()
    )
    # MODULE-046 - same "optional real adapter" principle: a real FFmpeg
    # assembly pipeline when the binary is available, a deterministic
    # placeholder otherwise, both behind the same `EpisodeAssembler`
    # Protocol so no caller code branches on which one is active.
    app.state.episode_assembler = (
        FFmpegAssembler(
            ffmpeg_path=settings.ffmpeg_path, timeout_seconds=settings.ffmpeg_timeout_seconds
        )
        if ffmpeg_is_available(settings.ffmpeg_path)
        else FakeAssembler()
    )
    # MODULE-048 - same principle, one more optional real adapter.
    app.state.media_inspector = (
        FFprobeInspector(
            ffprobe_path=settings.ffprobe_path, timeout_seconds=settings.ffmpeg_timeout_seconds
        )
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
        version="0.2.0",
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
    app.include_router(eval.router)
    app.include_router(media_eval.router)
    app.include_router(settings_router.router)
    app.include_router(chat.router)
    return app


app = create_app()
