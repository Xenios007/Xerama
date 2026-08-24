"""FastAPI application factory. See README.md "First end-to-end test"."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from xerama.api.routers import generation, inspect, projects
from xerama.config import ModelRoleRegistry, Settings, get_settings
from xerama.db.base import create_all, make_engine, make_session_factory
from xerama.pipeline.ai_gateway import AIGateway
from xerama.providers.health import ProviderHealthTracker
from xerama.providers.openrouter import OpenRouterProvider


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
    return app


app = create_app()
