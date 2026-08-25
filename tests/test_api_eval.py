"""MODULE-072 - eval endpoint tests.

A dedicated `client` fixture, not `test_api.py`'s - that fixture's
`FakeLLMProvider` is pre-loaded with the exact 9-response sequence
`generate-series` consumes; an eval test that doesn't call
generate-series would instead consume the front of that same queue
(wrong schemas entirely) if it shared the fixture. This fixture's queue
starts empty - each test queues exactly the responses its own eval run
needs.
"""

import json

import httpx
import pytest

import fixtures as fx
from xerama.api.app import create_app
from xerama.config import ModelRoleRegistry, Settings
from xerama.db.base import create_all, make_engine, make_session_factory
from xerama.eval.datasets import JUDGE_CASES
from xerama.pipeline.ai_gateway import AIGateway
from xerama.pipeline.rate_limiting import RateLimiter
from xerama.providers.fake import FakeLLMProvider
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

    provider = FakeLLMProvider([])
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
        ac.fake_provider = provider
        yield ac

    await engine.dispose()


@pytest.mark.asyncio
async def test_eval_run_dataset_and_benchmark_flow(client: httpx.AsyncClient) -> None:
    """A live eval run (fake provider in tests, "live eval opt-in" in
    production) persists one result per dataset case and the benchmark
    endpoint aggregates them by (role, provider, model)."""
    for _ in JUDGE_CASES:
        client.fake_provider.queue(json.dumps(fx.judge_result("A")))

    run = await client.post("/eval/roles/judge/run")
    assert run.status_code == 200, run.text
    results = run.json()
    assert len(results) == len(JUDGE_CASES)
    assert all(r["schema_valid"] for r in results)

    benchmark = await client.get("/eval/roles/judge/benchmark")
    assert benchmark.status_code == 200
    rows = benchmark.json()
    assert len(rows) == 1
    assert rows[0]["sample_count"] == len(JUDGE_CASES)
    assert rows[0]["schema_success_rate"] == 1.0

    run_id = results[0]["id"]
    preference = await client.post(
        f"/eval/runs/{run_id}/human-preference", params={"preference": "preferred"}
    )
    assert preference.status_code == 200
    assert preference.json()["human_preference"] == "preferred"


@pytest.mark.asyncio
async def test_eval_run_dataset_for_uncovered_role_returns_empty(client: httpx.AsyncClient) -> None:
    """CONTINUITY_CHECKER has no LLM call in this codebase to benchmark."""
    run = await client.post("/eval/roles/continuity_checker/run")
    assert run.status_code == 200
    assert run.json() == []


@pytest.mark.asyncio
async def test_eval_run_dataset_reports_schema_failure(client: httpx.AsyncClient) -> None:
    from xerama.providers.errors import ProviderError, ProviderErrorKind

    for _ in JUDGE_CASES:
        client.fake_provider.queue(ProviderError(ProviderErrorKind.AUTHENTICATION, "bad key"))

    run = await client.post("/eval/roles/judge/run")
    assert run.status_code == 200, run.text
    results = run.json()
    assert all(not r["schema_valid"] for r in results)
    assert all(r["error"] for r in results)
