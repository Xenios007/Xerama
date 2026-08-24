import json

import httpx
import pytest

import fixtures as fx
from xerama.api.app import create_app
from xerama.config import ModelRoleRegistry, Settings
from xerama.db.base import create_all, make_engine, make_session_factory
from xerama.pipeline.ai_gateway import AIGateway
from xerama.providers.fake import FakeLLMProvider
from xerama.providers.health import ProviderHealthTracker


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

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.fake_provider = provider  # exposed for tests that need to queue more responses
        yield ac

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_and_get_project(client: httpx.AsyncClient) -> None:
    response = await client.post("/projects", json={"name": "Trial 01", "description": "pilot"})
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Trial 01"

    fetched = await client.get(f"/projects/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


@pytest.mark.asyncio
async def test_get_project_404(client: httpx.AsyncClient) -> None:
    response = await client.get("/projects/does-not-exist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_series_end_to_end(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]

    response = await client.post(
        f"/projects/{project_id}/generate-series",
        json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["bible"]["title"] == "Blood Sisters"
    assert len(result["outlines"]) == 3

    series_id = result["series_id"]
    bible_response = await client.get(f"/series/{series_id}/bible")
    assert bible_response.status_code == 200
    assert bible_response.json()["title"] == "Blood Sisters"

    characters_response = await client.get(f"/series/{series_id}/characters")
    assert len(characters_response.json()["characters"]) == 2

    episodes_response = await client.get(f"/series/{series_id}/episodes")
    assert len(episodes_response.json()) == 3

    episode1_id = result["episode1_id"]
    shots_response = await client.get(f"/episodes/{episode1_id}/shots")
    assert shots_response.status_code == 200
    assert shots_response.json()["scenes"][0]["shots"][0]["camera"]["shot_size"] == "close-up"

    season_plan_response = await client.get(f"/series/{series_id}/season-plan")
    assert season_plan_response.status_code == 200
    season_body = season_plan_response.json()
    assert season_body["version"] == 1
    assert season_body["status"] == "draft"
    assert len(season_body["plan"]["episode_assignments"]) == 3

    versions_response = await client.get(f"/series/{series_id}/season-plan/versions")
    assert len(versions_response.json()) == 1

    approve_response = await client.post(f"/series/{series_id}/season-plan/1/approve")
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    current_after_approve = await client.get(f"/series/{series_id}/season-plan")
    assert current_after_approve.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_episode_engine_generate_next_and_regenerate(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    generated = await client.post(
        f"/projects/{project_id}/generate-series",
        json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
    )
    series_id = generated.json()["series_id"]

    client.fake_provider.queue(json.dumps(fx.script()))
    client.fake_provider.queue(json.dumps(fx.shot_plan()))
    response = await client.post(
        f"/series/{series_id}/episodes/generate-next", params={"project_id": project_id}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["episode_number"] == 2
    assert body["canon_committed"] is True

    episodes_response = await client.get(f"/series/{series_id}/episodes")
    statuses = {e["episode_number"]: e["status"] for e in episodes_response.json()}
    assert statuses[1] == "canon_committed"
    assert statuses[2] == "canon_committed"
    assert statuses[3] == "outlined"


@pytest.mark.asyncio
async def test_episode_engine_409_for_unknown_series(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    response = await client.post(
        "/series/does-not-exist/episodes/1/generate", params={"project_id": project_id}
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_season_plan_404_before_generation(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    response = await client.get(f"/series/{project_id}/season-plan")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_series_404_for_unknown_project(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/projects/does-not-exist/generate-series",
        json={"genre": "thriller"},
    )
    assert response.status_code == 404
