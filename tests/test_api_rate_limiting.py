"""MODULE-068 - rate-limit/concurrency/budget guard integration tests.

Uses a deliberately tight `RateLimiter`/budget ceiling (unlike the
permissive defaults every other API test runs under) to exercise the
429/402/409 paths end-to-end through `guarded_generation`. Project
bootstrap (`generate-series`) also goes through the request-rate check,
so tests that need to isolate one specific guard swap in a fresh
`RateLimiter` after setup rather than trying to pre-count setup's own
consumption.
"""

import json

import httpx
import pytest

import fixtures as fx
from xerama.api.app import create_app
from xerama.config import ModelRoleRegistry, Settings, get_settings
from xerama.db.base import create_all, make_engine, make_session_factory
from xerama.pipeline.ai_gateway import AIGateway
from xerama.pipeline.rate_limiting import RateLimiter
from xerama.providers.fake import FakeLLMProvider
from xerama.providers.fake_image import FakeImageProvider
from xerama.providers.fake_media_qc import FakeMediaQCProvider
from xerama.providers.health import ProviderHealthTracker
from xerama.providers.local_storage import LocalStorageProvider
from xerama.repositories.sqlalchemy_impl import SQLAlchemyCostRecordRepository
from xerama.services.media_router import MediaProviderRouter


async def _create_project_with_storyboard(client: httpx.AsyncClient) -> tuple[str, str]:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    generated = await client.post(
        f"/projects/{project_id}/generate-series",
        json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
    )
    episode1_id = generated.json()["episode1_id"]
    storyboard = await client.post(f"/episodes/{episode1_id}/scenes/1/shots/1/storyboard")
    return project_id, storyboard.json()["id"]


@pytest.fixture
async def client(tmp_path):
    app = create_app()
    db_path = tmp_path / "api_test.db"
    engine = make_engine(f"sqlite+aiosqlite:///{db_path}")
    await create_all(engine)
    session_factory = make_session_factory(engine)

    provider = FakeLLMProvider(
        [
            json.dumps(fx.concept("A")),
            json.dumps(fx.concept("B")),
            json.dumps(fx.judge_result("A")),
            json.dumps(fx.bible()),
            json.dumps(fx.cast()),
            json.dumps(fx.season_plan()),
            json.dumps(fx.outline_set(3)),
            json.dumps(fx.script()),
            json.dumps(fx.shot_plan()),
        ]
    )
    gateway = AIGateway(provider=provider, roles=ModelRoleRegistry(Settings()), health=ProviderHealthTracker())

    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.ai_gateway = gateway
    app.state.storage_provider = LocalStorageProvider(tmp_path / "storage")
    image_provider = FakeImageProvider()
    app.state.image_router = MediaProviderRouter([image_provider])
    app.state.video_router = MediaProviderRouter([])
    app.state.voice_router = MediaProviderRouter([])
    app.state.lip_sync_router = MediaProviderRouter([])
    app.state.media_qc_provider = FakeMediaQCProvider()
    app.state.episode_assembler = None
    app.state.media_inspector = None
    # Generous during setup (`generate-series` itself goes through the
    # same request-rate check) - individual tests swap in a tighter
    # `RateLimiter` afterward to isolate the guard they're exercising.
    app.state.rate_limiter = RateLimiter(
        requests_per_window=1000, window_seconds=60.0, max_concurrent_per_project=1000
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.app = app
        ac.fake_image_provider = image_provider
        yield ac

    await engine.dispose()


@pytest.mark.asyncio
async def test_request_rate_limit_returns_429_with_retry_after(client: httpx.AsyncClient) -> None:
    project_id, storyboard_id = await _create_project_with_storyboard(client)
    client.app.state.rate_limiter = RateLimiter(
        requests_per_window=1, window_seconds=60.0, max_concurrent_per_project=1000
    )

    client.fake_image_provider.queue(b"keyframe bytes")
    first = await client.post(f"/storyboards/{storyboard_id}/keyframes/generate")
    assert first.status_code == 200, first.text

    second = await client.post(f"/storyboards/{storyboard_id}/keyframes/generate")
    assert second.status_code == 429, second.text
    assert "Retry-After" in second.headers


@pytest.mark.asyncio
async def test_budget_ceiling_returns_402(client: httpx.AsyncClient, monkeypatch) -> None:
    project_id, storyboard_id = await _create_project_with_storyboard(client)

    # Seed prior spend directly - the fixture's AIGateway has no
    # cost_recorder wired, so generate-series above recorded nothing;
    # the budget guard needs real prior spend to have something to
    # exceed.
    async with client.app.state.session_factory() as session:
        await SQLAlchemyCostRecordRepository(session).create(
            provider="p", model="m", stage="image_generation", project_id=project_id,
            cost_usd=1.0, cost_known=True,
        )
        await session.commit()

    get_settings.cache_clear()
    monkeypatch.setenv("PROJECT_BUDGET_CEILING_USD", "0.5")
    get_settings.cache_clear()
    try:
        client.fake_image_provider.queue(b"keyframe bytes")
        response = await client.post(f"/storyboards/{storyboard_id}/keyframes/generate")
        assert response.status_code == 402, response.text
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_duplicate_generation_request_is_rejected(client: httpx.AsyncClient) -> None:
    """MODULE-068 "duplicate-generation suppression" - an identical
    generation request already marked in-flight is rejected rather than
    reaching the provider a second time. Simulates the "already in
    flight" state directly on the shared `RateLimiter` (the same
    mechanism `RateLimiter.suppress_duplicate` uses - see
    test_rate_limiting.py for that class's own unit tests) rather than
    racing two real concurrent HTTP requests, which would also race an
    unrelated, pre-existing TOCTOU in `StyleBibleRepository.get_or_create`
    (two concurrent first-time callers for the same series both trying
    to insert - out of scope here)."""
    project_id, storyboard_id = await _create_project_with_storyboard(client)

    duplicate_key = f"{project_id}:keyframe:{storyboard_id}"
    async with client.app.state.rate_limiter.suppress_duplicate(duplicate_key):
        client.fake_image_provider.queue(b"keyframe bytes")
        response = await client.post(f"/storyboards/{storyboard_id}/keyframes/generate")
    assert response.status_code == 409, response.text

    # The lock is released once the `async with` above exits - the same
    # request now succeeds.
    client.fake_image_provider.queue(b"keyframe bytes")
    retried = await client.post(f"/storyboards/{storyboard_id}/keyframes/generate")
    assert retried.status_code == 200, retried.text
