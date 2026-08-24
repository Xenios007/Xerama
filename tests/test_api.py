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
from xerama.providers.local_storage import LocalStorageProvider


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

    generation_requests_response = await client.get(f"/episodes/{episode1_id}/generation-requests")
    assert generation_requests_response.status_code == 200
    compiled = generation_requests_response.json()
    assert len(compiled) == 1
    assert "close-up" in compiled[0]["prompt"]
    assert compiled[0]["references"]["character_asset_ids"] == ["CHAR_001"]

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


@pytest.mark.asyncio
async def test_asset_upload_download_accept_reject_delete_flow(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]

    upload = await client.post(
        "/assets/upload",
        params={"project_id": project_id, "asset_type": "image"},
        files={"file": ("frame.png", b"fake png bytes", "image/png")},
    )
    assert upload.status_code == 200, upload.text
    asset = upload.json()
    assert asset["mime_type"] == "image/png"
    assert asset["provenance"]["provider"] == "manual_upload"
    asset_id = asset["id"]

    listed = await client.get("/assets", params={"project_id": project_id})
    assert len(listed.json()) == 1

    fetched = await client.get(f"/assets/{asset_id}")
    assert fetched.status_code == 200

    downloaded = await client.get(f"/assets/{asset_id}/download")
    assert downloaded.status_code == 200
    assert downloaded.content == b"fake png bytes"

    accepted = await client.post(f"/assets/{asset_id}/accept")
    assert accepted.json()["status"] == "accepted"

    protected_delete = await client.delete(f"/assets/{asset_id}")
    assert protected_delete.status_code == 409

    forced_delete = await client.delete(f"/assets/{asset_id}", params={"force": True})
    assert forced_delete.status_code == 204

    assert (await client.get(f"/assets/{asset_id}")).status_code == 404


@pytest.mark.asyncio
async def test_asset_reject_records_reason(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    upload = await client.post(
        "/assets/upload",
        params={"project_id": project_id, "asset_type": "video"},
        files={"file": ("clip.mp4", b"fake mp4 bytes", "video/mp4")},
    )
    asset_id = upload.json()["id"]

    rejected = await client.post(f"/assets/{asset_id}/reject", params={"reason": "face drift"})
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["rejection_reason"] == "face drift"


@pytest.mark.asyncio
async def test_asset_not_found_404s(client: httpx.AsyncClient) -> None:
    assert (await client.get("/assets/does-not-exist")).status_code == 404
    assert (await client.get("/assets/does-not-exist/download")).status_code == 404
    assert (await client.post("/assets/does-not-exist/accept")).status_code == 404


@pytest.mark.asyncio
async def test_character_lock_blocks_identity_update_until_recast(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    generated = await client.post(
        f"/projects/{project_id}/generate-series",
        json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
    )
    series_id = generated.json()["series_id"]
    characters = (await client.get(f"/series/{series_id}/characters")).json()["characters"]
    character_id = characters[0]["id"]

    fetched = await client.get(f"/characters/{character_id}")
    assert fetched.status_code == 200
    assert fetched.json()["locked"] is False
    assert fetched.json()["version"] == 1

    identity_update = await client.patch(
        f"/characters/{character_id}/identity", json={"visual_identity_id": "asset-root"}
    )
    assert identity_update.status_code == 200
    assert identity_update.json()["visual_identity_id"] == "asset-root"

    locked = await client.post(f"/characters/{character_id}/lock")
    assert locked.status_code == 200
    assert locked.json()["locked"] is True

    blocked = await client.patch(
        f"/characters/{character_id}/identity", json={"visual_identity_id": "asset-root-2"}
    )
    assert blocked.status_code == 409

    recast = await client.post(f"/characters/{character_id}/unlock")
    assert recast.status_code == 200
    assert recast.json()["locked"] is False
    assert recast.json()["version"] == 2

    allowed = await client.patch(
        f"/characters/{character_id}/identity", json={"visual_identity_id": "asset-root-2"}
    )
    assert allowed.status_code == 200
    assert allowed.json()["visual_identity_id"] == "asset-root-2"


@pytest.mark.asyncio
async def test_character_wardrobe_and_physical_state_variants(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    generated = await client.post(
        f"/projects/{project_id}/generate-series",
        json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
    )
    series_id = generated.json()["series_id"]
    character_id = (await client.get(f"/series/{series_id}/characters")).json()["characters"][0]["id"]

    wardrobe = await client.post(
        f"/characters/{character_id}/wardrobe",
        json={"label": "office_black_dress", "reference_asset_ids": ["asset-w1"]},
    )
    assert wardrobe.status_code == 200, wardrobe.text
    assert wardrobe.json()["label"] == "office_black_dress"

    state = await client.post(
        f"/characters/{character_id}/physical-states",
        json={"label": "injured", "reference_asset_ids": ["asset-s1"]},
    )
    assert state.status_code == 200
    assert state.json()["label"] == "injured"

    listed_wardrobe = await client.get(f"/characters/{character_id}/wardrobe")
    assert [v["label"] for v in listed_wardrobe.json()] == ["office_black_dress"]

    listed_states = await client.get(f"/characters/{character_id}/physical-states")
    assert [v["label"] for v in listed_states.json()] == ["injured"]


@pytest.mark.asyncio
async def test_character_not_found_404s(client: httpx.AsyncClient) -> None:
    assert (await client.get("/characters/does-not-exist")).status_code == 404
    assert (await client.post("/characters/does-not-exist/lock")).status_code == 404
    assert (
        await client.patch("/characters/does-not-exist/identity", json={"visual_identity_id": "x"})
    ).status_code == 404
