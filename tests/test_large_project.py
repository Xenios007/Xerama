"""MODULE-070 - "validate large projects" smoke tests.

Not a load test (no CI infrastructure to run one against - see this
module's "appropriate to local CI resources" verification bar); these
confirm that scaling a project's size (many episodes, many assets)
doesn't blow up (timeout, O(n^2) query pattern, unhandled exception) at
a scale well past the 3-episode fixtures every other API test uses.
"""

import json
import time

import httpx
import pytest

import fixtures as fx
from xerama.api.app import create_app
from xerama.config import ModelRoleRegistry, Settings
from xerama.db.base import create_all, make_engine, make_session_factory
from xerama.domain.asset import AssetOwnership, AssetProvenance, AssetType
from xerama.pipeline.ai_gateway import AIGateway
from xerama.pipeline.rate_limiting import RateLimiter
from xerama.providers.fake import FakeLLMProvider
from xerama.providers.health import ProviderHealthTracker
from xerama.providers.local_storage import LocalStorageProvider
from xerama.repositories.sqlalchemy_impl import SQLAlchemyAssetRepository
from xerama.services.asset_service import AssetService
from xerama.services.media_router import MediaProviderRouter

LARGE_EPISODE_COUNT = 40


@pytest.fixture
async def client(tmp_path):
    app = create_app()
    db_path = tmp_path / "api_test.db"
    engine = make_engine(f"sqlite+aiosqlite:///{db_path}")
    await create_all(engine)
    session_factory = make_session_factory(engine)

    # Only episode 1 auto-generates end-to-end (documented behavior -
    # episodes 2..N require an explicit follow-up call), so a larger
    # episode_count needs no extra script/shot_plan responses queued -
    # only a bigger outline_set.
    provider = FakeLLMProvider(
        [
            json.dumps(fx.concept("A")),
            json.dumps(fx.concept("B")),
            json.dumps(fx.judge_result("A")),
            json.dumps(fx.bible()),
            json.dumps(fx.cast()),
            json.dumps(fx.season_plan()),
            json.dumps(fx.outline_set(LARGE_EPISODE_COUNT)),
            json.dumps(fx.script()),
            json.dumps(fx.shot_plan()),
        ]
    )
    gateway = AIGateway(provider=provider, roles=ModelRoleRegistry(Settings()), health=ProviderHealthTracker())

    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.ai_gateway = gateway
    app.state.storage_provider = LocalStorageProvider(tmp_path / "storage")
    app.state.image_router = MediaProviderRouter([])
    app.state.video_router = MediaProviderRouter([])
    app.state.voice_router = MediaProviderRouter([])
    app.state.lip_sync_router = MediaProviderRouter([])
    app.state.media_qc_provider = None
    app.state.episode_assembler = None
    app.state.media_inspector = None
    app.state.rate_limiter = RateLimiter(
        requests_per_window=1000, window_seconds=60.0, max_concurrent_per_project=1000
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.app = app
        yield ac

    await engine.dispose()


@pytest.mark.asyncio
async def test_generate_series_with_many_episodes_completes_quickly(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Large Project"})
    project_id = created.json()["id"]

    started = time.monotonic()
    generated = await client.post(
        f"/projects/{project_id}/generate-series",
        json={
            "genre": "thriller",
            "episode_count": LARGE_EPISODE_COUNT,
            "episode_duration_seconds": 75,
        },
    )
    elapsed = time.monotonic() - started

    assert generated.status_code == 200, generated.text
    series_id = generated.json()["series_id"]
    assert elapsed < 10.0, f"generate-series with {LARGE_EPISODE_COUNT} episodes took {elapsed:.2f}s"

    episodes = await client.get(f"/series/{series_id}/episodes")
    assert episodes.status_code == 200
    assert len(episodes.json()) == LARGE_EPISODE_COUNT


@pytest.mark.asyncio
async def test_listing_many_assets_for_one_project_completes_quickly(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Large Project"})
    project_id = created.json()["id"]

    asset_count = 300
    async with client.app.state.session_factory() as session:
        asset_service = AssetService(
            storage=client.app.state.storage_provider, asset_repo=SQLAlchemyAssetRepository(session)
        )
        for i in range(asset_count):
            await asset_service.ingest_bytes(
                f"asset {i}".encode(),
                AssetType.IMAGE,
                AssetOwnership(project_id=project_id),
                provenance=AssetProvenance(provider="fake_image"),
                mime_type="image/png",
                ext=".png",
            )
        await session.commit()

    started = time.monotonic()
    listed = await client.get("/assets", params={"project_id": project_id})
    elapsed = time.monotonic() - started

    assert listed.status_code == 200
    assert len(listed.json()) == asset_count
    assert elapsed < 5.0, f"listing {asset_count} assets took {elapsed:.2f}s"
