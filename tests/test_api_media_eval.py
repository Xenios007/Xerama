"""MODULE-073 - media eval endpoint tests. Dedicated minimal `client`
fixture - no LLM provider queue is needed (media eval never calls the
AIGateway)."""

import httpx
import pytest

from xerama.api.app import create_app
from xerama.config import ModelRoleRegistry, Settings
from xerama.db.base import create_all, make_engine, make_session_factory
from xerama.eval.media_datasets import IMAGE_CASES
from xerama.pipeline.ai_gateway import AIGateway
from xerama.pipeline.rate_limiting import RateLimiter
from xerama.providers.fake import FakeLLMProvider
from xerama.providers.fake_image import FakeImageProvider
from xerama.providers.fake_media_qc import FakeMediaQCProvider
from xerama.providers.health import ProviderHealthTracker
from xerama.providers.local_storage import LocalStorageProvider
from xerama.services.media_router import MediaProviderRouter


@pytest.fixture
async def client(tmp_path):
    app = create_app()
    db_path = tmp_path / "api_test.db"
    engine = make_engine(f"sqlite+aiosqlite:///{db_path}")
    await create_all(engine)
    session_factory = make_session_factory(engine)

    gateway = AIGateway(
        provider=FakeLLMProvider([]), roles=ModelRoleRegistry(Settings()), health=ProviderHealthTracker()
    )

    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.ai_gateway = gateway
    app.state.storage_provider = LocalStorageProvider(tmp_path / "storage")
    app.state.image_router = MediaProviderRouter([FakeImageProvider()])
    app.state.video_router = MediaProviderRouter([])
    app.state.voice_router = MediaProviderRouter([])
    app.state.lip_sync_router = MediaProviderRouter([])
    app.state.media_qc_provider = FakeMediaQCProvider()
    app.state.episode_assembler = None
    app.state.media_inspector = None
    app.state.rate_limiter = RateLimiter(
        requests_per_window=1000, window_seconds=60.0, max_concurrent_per_project=1000
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await engine.dispose()


@pytest.mark.asyncio
async def test_media_eval_run_and_benchmark_flow(client: httpx.AsyncClient) -> None:
    run = await client.post("/media-eval/image/run")
    assert run.status_code == 200, run.text
    results = run.json()
    assert len(results) == len(IMAGE_CASES)
    assert all(r["generation_succeeded"] for r in results)
    assert all(r["accepted"] for r in results)  # FakeMediaQCProvider defaults to PASS

    benchmark = await client.get("/media-eval/benchmark")
    assert benchmark.status_code == 200
    rows = benchmark.json()
    covered_classes = {row["shot_class"] for row in rows}
    assert covered_classes == {c.shot_class.value for c in IMAGE_CASES}

    run_id = results[0]["id"]
    preference = await client.post(
        f"/media-eval/runs/{run_id}/human-preference", params={"preference": "preferred"}
    )
    assert preference.status_code == 200
    assert preference.json()["human_preference"] == "preferred"


@pytest.mark.asyncio
async def test_media_eval_run_video_dataset(client: httpx.AsyncClient) -> None:
    """No video provider registered in this fixture - every case fails
    generation cleanly rather than the endpoint erroring."""
    run = await client.post("/media-eval/video/run")
    assert run.status_code == 200, run.text
    results = run.json()
    assert len(results) >= 1
    assert all(not r["generation_succeeded"] for r in results)
    assert all(r["error"] for r in results)
