import json

import httpx
import pytest

import fixtures as fx
from xerama.api.app import create_app
from xerama.config import ModelRoleRegistry, Settings
from xerama.db.base import create_all, make_engine, make_session_factory
from xerama.pipeline.ai_gateway import AIGateway
from xerama.providers.fake import FakeLLMProvider
from xerama.providers.fake_frame_extractor import FakeFrameExtractor
from xerama.providers.fake_image import FakeImageProvider
from xerama.providers.fake_lip_sync import FakeLipSyncProvider
from xerama.providers.fake_video import FakeVideoProvider
from xerama.providers.fake_voice import FakeVoiceProvider
from xerama.providers.health import ProviderHealthTracker
from xerama.providers.image import ImageProviderCapabilities
from xerama.providers.local_storage import LocalStorageProvider
from xerama.services.media_router import MediaProviderRouter


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
    image_provider = FakeImageProvider(
        capabilities=ImageProviderCapabilities(supports_edit=True, supports_mask=True)
    )
    app.state.image_router = MediaProviderRouter([image_provider])
    video_provider = FakeVideoProvider()
    app.state.video_router = MediaProviderRouter([video_provider])
    app.state.frame_extractor = FakeFrameExtractor()
    voice_provider = FakeVoiceProvider()
    app.state.voice_router = MediaProviderRouter([voice_provider])
    lip_sync_provider = FakeLipSyncProvider()
    app.state.lip_sync_router = MediaProviderRouter([lip_sync_provider])

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.fake_provider = provider  # exposed for tests that need to queue more responses
        ac.fake_image_provider = image_provider
        ac.fake_voice_provider = voice_provider
        ac.fake_lip_sync_provider = lip_sync_provider
        ac.fake_video_provider = video_provider
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


@pytest.mark.asyncio
async def test_style_bible_lock_blocks_update_until_recast(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    generated = await client.post(
        f"/projects/{project_id}/generate-series",
        json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
    )
    series_id = generated.json()["series_id"]

    fetched = await client.get(f"/series/{series_id}/style-bible")
    assert fetched.status_code == 200
    assert fetched.json()["locked"] is False

    updated = await client.patch(
        f"/series/{series_id}/style-bible", json={"style_dna": "neon noir", "palette": ["#111", "#f2e"]}
    )
    assert updated.status_code == 200
    assert updated.json()["style_dna"] == "neon noir"

    locked = await client.post(f"/series/{series_id}/style-bible/lock")
    assert locked.status_code == 200
    assert locked.json()["locked"] is True

    blocked = await client.patch(f"/series/{series_id}/style-bible", json={"style_dna": "another look"})
    assert blocked.status_code == 409

    recast = await client.post(f"/series/{series_id}/style-bible/unlock")
    assert recast.json()["locked"] is False
    assert recast.json()["version"] == 2


@pytest.mark.asyncio
async def test_storyboard_keyframe_generate_accept_flow(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    generated = await client.post(
        f"/projects/{project_id}/generate-series",
        json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
    )
    episode1_id = generated.json()["episode1_id"]

    created_storyboard = await client.post(
        f"/episodes/{episode1_id}/scenes/1/shots/1/storyboard",
        json={"layout_description": "wide establishing, letter close-up"},
    )
    assert created_storyboard.status_code == 200, created_storyboard.text
    storyboard = created_storyboard.json()
    assert storyboard["status"] == "draft"
    storyboard_id = storyboard["id"]

    idempotent = await client.post(f"/episodes/{episode1_id}/scenes/1/shots/1/storyboard")
    assert idempotent.json()["id"] == storyboard_id

    listed = await client.get(f"/episodes/{episode1_id}/storyboards")
    assert len(listed.json()) == 1

    client.fake_image_provider.queue(b"generated keyframe bytes")
    generated_keyframe = await client.post(f"/storyboards/{storyboard_id}/keyframes/generate")
    assert generated_keyframe.status_code == 200, generated_keyframe.text
    asset = generated_keyframe.json()
    assert asset["take_number"] == 1
    assert asset["status"] == "pending"

    keyframes = await client.get(f"/storyboards/{storyboard_id}/keyframes")
    assert len(keyframes.json()) == 1

    accepted = await client.post(f"/storyboards/{storyboard_id}/keyframes/{asset['id']}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "approved"
    assert accepted.json()["approved_keyframe_asset_id"] == asset["id"]


@pytest.mark.asyncio
async def test_storyboard_keyframe_reject_and_manual_upload_retry(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    generated = await client.post(
        f"/projects/{project_id}/generate-series",
        json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
    )
    episode1_id = generated.json()["episode1_id"]
    storyboard_id = (
        await client.post(f"/episodes/{episode1_id}/scenes/1/shots/1/storyboard")
    ).json()["id"]

    client.fake_image_provider.queue(b"bad take")
    first = (await client.post(f"/storyboards/{storyboard_id}/keyframes/generate")).json()

    rejected = await client.post(
        f"/storyboards/{storyboard_id}/keyframes/{first['id']}/reject", params={"reason": "face drift"}
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    still_draft = await client.get(f"/storyboards/{storyboard_id}")
    assert still_draft.json()["status"] == "draft"

    retry_upload = await client.post(
        f"/storyboards/{storyboard_id}/keyframes/upload",
        files={"file": ("retake.png", b"manual retake bytes", "image/png")},
    )
    assert retry_upload.status_code == 200, retry_upload.text
    assert retry_upload.json()["take_number"] == 2
    assert retry_upload.json()["provenance"]["provider"] == "manual_upload"


@pytest.mark.asyncio
async def test_storyboard_keyframe_edit_flow(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    generated = await client.post(
        f"/projects/{project_id}/generate-series",
        json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
    )
    episode1_id = generated.json()["episode1_id"]
    storyboard_id = (
        await client.post(f"/episodes/{episode1_id}/scenes/1/shots/1/storyboard")
    ).json()["id"]

    base = (
        await client.post(
            f"/storyboards/{storyboard_id}/keyframes/upload",
            files={"file": ("base.png", b"original bytes", "image/png")},
        )
    ).json()
    accepted = await client.post(f"/storyboards/{storyboard_id}/keyframes/{base['id']}/accept")
    assert accepted.status_code == 200

    client.fake_image_provider.queue(b"edited bytes")
    edited = await client.post(
        f"/storyboards/{storyboard_id}/keyframes/edit",
        json={"instruction": "fix the left hand", "base_asset_id": base["id"]},
    )
    assert edited.status_code == 200, edited.text
    edited_asset = edited.json()
    assert edited_asset["take_number"] == 2
    assert edited_asset["provenance"]["generation_params"]["edit"] is True
    assert edited_asset["provenance"]["generation_params"]["based_on_take"] == base["id"]

    # The accepted base take is untouched.
    still_approved = await client.get(f"/storyboards/{storyboard_id}")
    assert still_approved.json()["approved_keyframe_asset_id"] == base["id"]
    base_download = await client.get(f"/assets/{base['id']}/download")
    assert base_download.content == b"original bytes"


@pytest.mark.asyncio
async def test_storyboard_keyframe_edit_rejects_unsupported_provider(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    generated = await client.post(
        f"/projects/{project_id}/generate-series",
        json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
    )
    episode1_id = generated.json()["episode1_id"]
    storyboard_id = (
        await client.post(f"/episodes/{episode1_id}/scenes/1/shots/1/storyboard")
    ).json()["id"]
    base = (
        await client.post(
            f"/storyboards/{storyboard_id}/keyframes/upload",
            files={"file": ("base.png", b"original bytes", "image/png")},
        )
    ).json()

    client.fake_image_provider.capabilities.supports_edit = False
    response = await client.post(
        f"/storyboards/{storyboard_id}/keyframes/edit",
        json={"instruction": "fix it", "base_asset_id": base["id"]},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_storyboard_not_found_404s(client: httpx.AsyncClient) -> None:
    assert (await client.get("/storyboards/does-not-exist")).status_code == 404
    assert (await client.post("/storyboards/does-not-exist/keyframes/generate")).status_code == 404


@pytest.mark.asyncio
async def test_video_production_generate_accept_flow(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    generated = await client.post(
        f"/projects/{project_id}/generate-series",
        json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
    )
    episode1_id = generated.json()["episode1_id"]

    created_production = await client.post(
        f"/episodes/{episode1_id}/scenes/1/shots/1/video-production"
    )
    assert created_production.status_code == 200, created_production.text
    production = created_production.json()
    assert production["status"] == "draft"
    production_id = production["id"]

    idempotent = await client.post(f"/episodes/{episode1_id}/scenes/1/shots/1/video-production")
    assert idempotent.json()["id"] == production_id

    listed = await client.get(f"/episodes/{episode1_id}/video-productions")
    assert len(listed.json()) == 1

    client.fake_video_provider.queue(b"generated take bytes")
    generated_take = await client.post(f"/video-productions/{production_id}/takes/generate")
    assert generated_take.status_code == 200, generated_take.text
    asset = generated_take.json()
    assert asset["take_number"] == 1
    assert asset["status"] == "pending"
    assert asset["type"] == "video"

    takes = await client.get(f"/video-productions/{production_id}/takes")
    assert len(takes.json()) == 1

    accepted = await client.post(f"/video-productions/{production_id}/takes/{asset['id']}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "approved"
    assert accepted.json()["approved_take_asset_id"] == asset["id"]
    # No continuity_group on this fixture shot - never extracts a frame.
    assert accepted.json()["extracted_last_frame_asset_id"] is None

    audio_production_id = (
        await client.post(f"/episodes/{episode1_id}/scenes/1/shots/1/audio-production")
    ).json()["id"]
    client.fake_voice_provider.queue(b"dialogue audio")
    audio_asset = (
        await client.post(
            f"/audio-productions/{audio_production_id}/takes/generate",
            json={"character_id": "CHAR_001"},
        )
    ).json()

    client.fake_lip_sync_provider.queue(b"lip synced clip")
    synced = await client.post(
        f"/video-productions/{production_id}/takes/lip-sync",
        json={
            "source_video_asset_id": asset["id"],
            "source_audio_asset_id": audio_asset["id"],
            "duration_seconds": 5.0,
            "character_id": "CHAR_001",
        },
    )
    assert synced.status_code == 200, synced.text
    synced_asset = synced.json()
    assert synced_asset["take_number"] == 2
    assert synced_asset["provenance"]["generation_params"]["lip_synced"] is True
    assert synced_asset["provenance"]["source_reference_asset_ids"] == [asset["id"], audio_asset["id"]]


@pytest.mark.asyncio
async def test_video_production_reject_and_manual_upload_retry(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    generated = await client.post(
        f"/projects/{project_id}/generate-series",
        json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
    )
    episode1_id = generated.json()["episode1_id"]
    production_id = (
        await client.post(f"/episodes/{episode1_id}/scenes/1/shots/1/video-production")
    ).json()["id"]

    client.fake_video_provider.queue(b"bad take")
    first = (await client.post(f"/video-productions/{production_id}/takes/generate")).json()

    rejected = await client.post(
        f"/video-productions/{production_id}/takes/{first['id']}/reject",
        params={"reason": "flicker artifact"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    still_draft = await client.get(f"/video-productions/{production_id}")
    assert still_draft.json()["status"] == "draft"

    retry_upload = await client.post(
        f"/video-productions/{production_id}/takes/upload",
        files={"file": ("retake.mp4", b"manual retake bytes", "video/mp4")},
    )
    assert retry_upload.status_code == 200, retry_upload.text
    assert retry_upload.json()["take_number"] == 2
    assert retry_upload.json()["provenance"]["provider"] == "manual_upload"


@pytest.mark.asyncio
async def test_video_production_not_found_404s(client: httpx.AsyncClient) -> None:
    assert (await client.get("/video-productions/does-not-exist")).status_code == 404
    assert (await client.post("/video-productions/does-not-exist/takes/generate")).status_code == 404


@pytest.mark.asyncio
async def test_voice_profile_lock_blocks_update_until_recast(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    generated = await client.post(
        f"/projects/{project_id}/generate-series",
        json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
    )
    series_id = generated.json()["series_id"]
    character_id = (await client.get(f"/series/{series_id}/characters")).json()["characters"][0]["id"]

    fetched = await client.get(f"/characters/{character_id}/voice-profile")
    assert fetched.status_code == 200
    assert fetched.json()["locked"] is False

    updated = await client.patch(
        f"/characters/{character_id}/voice-profile", json={"provider_voice_id": "v1"}
    )
    assert updated.status_code == 200
    assert updated.json()["provider_voice_id"] == "v1"

    locked = await client.post(f"/characters/{character_id}/voice-profile/lock")
    assert locked.json()["locked"] is True

    blocked = await client.patch(
        f"/characters/{character_id}/voice-profile", json={"provider_voice_id": "v2"}
    )
    assert blocked.status_code == 409

    recast = await client.post(f"/characters/{character_id}/voice-profile/unlock")
    assert recast.json()["locked"] is False
    assert recast.json()["version"] == 2


@pytest.mark.asyncio
async def test_audio_production_generate_accept_flow(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    generated = await client.post(
        f"/projects/{project_id}/generate-series",
        json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
    )
    episode1_id = generated.json()["episode1_id"]

    created_production = await client.post(
        f"/episodes/{episode1_id}/scenes/1/shots/1/audio-production"
    )
    assert created_production.status_code == 200, created_production.text
    production = created_production.json()
    assert production["status"] == "draft"
    production_id = production["id"]

    idempotent = await client.post(f"/episodes/{episode1_id}/scenes/1/shots/1/audio-production")
    assert idempotent.json()["id"] == production_id

    client.fake_voice_provider.queue(b"synthesized dialogue")
    generated_take = await client.post(
        f"/audio-productions/{production_id}/takes/generate", json={"character_id": "CHAR_001"}
    )
    assert generated_take.status_code == 200, generated_take.text
    asset = generated_take.json()
    assert asset["take_number"] == 1
    assert asset["type"] == "audio"

    takes = await client.get(f"/audio-productions/{production_id}/takes")
    assert len(takes.json()) == 1

    accepted = await client.post(f"/audio-productions/{production_id}/takes/{asset['id']}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "approved"
    assert accepted.json()["approved_take_asset_id"] == asset["id"]


@pytest.mark.asyncio
async def test_audio_production_reject_and_manual_upload_retry(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    generated = await client.post(
        f"/projects/{project_id}/generate-series",
        json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
    )
    episode1_id = generated.json()["episode1_id"]
    production_id = (
        await client.post(f"/episodes/{episode1_id}/scenes/1/shots/1/audio-production")
    ).json()["id"]

    client.fake_voice_provider.queue(b"bad take")
    first = (
        await client.post(
            f"/audio-productions/{production_id}/takes/generate", json={"character_id": "CHAR_001"}
        )
    ).json()

    rejected = await client.post(
        f"/audio-productions/{production_id}/takes/{first['id']}/reject",
        params={"reason": "mispronounced name"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    still_draft = await client.get(f"/audio-productions/{production_id}")
    assert still_draft.json()["status"] == "draft"

    retry_upload = await client.post(
        f"/audio-productions/{production_id}/takes/upload",
        files={"file": ("retake.mp3", b"manual retake bytes", "audio/mpeg")},
    )
    assert retry_upload.status_code == 200, retry_upload.text
    assert retry_upload.json()["take_number"] == 2
    assert retry_upload.json()["provenance"]["provider"] == "manual_upload"


@pytest.mark.asyncio
async def test_audio_production_not_found_404s(client: httpx.AsyncClient) -> None:
    assert (await client.get("/audio-productions/does-not-exist")).status_code == 404
    assert (
        await client.post(
            "/audio-productions/does-not-exist/takes/generate", json={"character_id": "CHAR_001"}
        )
    ).status_code == 404


@pytest.mark.asyncio
async def test_music_cue_create_link_approve_flow(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    generated = await client.post(
        f"/projects/{project_id}/generate-series",
        json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
    )
    episode1_id = generated.json()["episode1_id"]

    created_cue = await client.post(
        f"/episodes/{episode1_id}/music-cues",
        json={"purpose": "tension build", "mood": "dread", "start_seconds": 0.0, "end_seconds": 10.0},
    )
    assert created_cue.status_code == 200, created_cue.text
    cue = created_cue.json()
    assert cue["status"] == "draft"

    listed = await client.get(f"/episodes/{episode1_id}/music-cues")
    assert len(listed.json()) == 1

    not_ready = await client.post(f"/music-cues/{cue['id']}/approve")
    assert not_ready.status_code == 409

    linked = await client.post(
        f"/music-cues/{cue['id']}/link-asset",
        json={"asset_id": "asset-1", "rights": {"license_type": "royalty_free"}},
    )
    assert linked.status_code == 200

    approved = await client.post(f"/music-cues/{cue['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    deleted = await client.delete(f"/music-cues/{cue['id']}")
    assert deleted.status_code == 204
    assert (await client.get(f"/music-cues/{cue['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_music_cue_not_found_404s(client: httpx.AsyncClient) -> None:
    assert (await client.get("/music-cues/does-not-exist")).status_code == 404
    assert (await client.post("/music-cues/does-not-exist/approve")).status_code == 404


@pytest.mark.asyncio
async def test_sound_effect_cue_derive_link_approve_flow(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    generated = await client.post(
        f"/projects/{project_id}/generate-series",
        json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
    )
    episode1_id = generated.json()["episode1_id"]

    derived = await client.post(
        f"/episodes/{episode1_id}/scenes/1/shots/1/sound-effect-cues/derive"
    )
    assert derived.status_code == 200, derived.text
    # The fixture shot's action ("Mara opens the letter") has no SFX keyword matches.
    assert derived.json() == []

    created_cue = await client.post(
        f"/episodes/{episode1_id}/sound-effect-cues",
        json={"scene_number": 1, "description": "paper rustle", "start_seconds": 0.0, "end_seconds": 0.5},
    )
    assert created_cue.status_code == 200, created_cue.text
    cue = created_cue.json()

    listed = await client.get(f"/episodes/{episode1_id}/sound-effect-cues")
    assert len(listed.json()) == 1

    not_ready = await client.post(f"/sound-effect-cues/{cue['id']}/approve")
    assert not_ready.status_code == 409

    await client.post(
        f"/sound-effect-cues/{cue['id']}/link-asset",
        json={"asset_id": "asset-1", "rights": {"license_type": "cc0"}},
    )
    approved = await client.post(f"/sound-effect-cues/{cue['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_sound_effect_cue_not_found_404s(client: httpx.AsyncClient) -> None:
    assert (await client.get("/sound-effect-cues/does-not-exist")).status_code == 404
    assert (await client.post("/sound-effect-cues/does-not-exist/approve")).status_code == 404


@pytest.mark.asyncio
async def test_subtitle_generate_list_export_validate_flow(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    generated = await client.post(
        f"/projects/{project_id}/generate-series",
        json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
    )
    episode1_id = generated.json()["episode1_id"]

    generated_subs = await client.post(f"/episodes/{episode1_id}/subtitles/generate")
    assert generated_subs.status_code == 200, generated_subs.text
    cues = generated_subs.json()
    assert len(cues) == 1
    assert cues[0]["text"] == "This can't be real."

    listed = await client.get(f"/episodes/{episode1_id}/subtitles")
    assert len(listed.json()) == 1

    srt = await client.get(f"/episodes/{episode1_id}/subtitles/export.srt")
    assert srt.status_code == 200
    assert "This can't be real." in srt.text
    assert "-->" in srt.text

    validated = await client.get(f"/episodes/{episode1_id}/subtitles/validate")
    assert validated.status_code == 200
    assert validated.json()["status"] == "pass"

    # Regenerating replaces rather than accumulates.
    regenerated = await client.post(f"/episodes/{episode1_id}/subtitles/generate")
    assert len(regenerated.json()) == 1
    still_listed = await client.get(f"/episodes/{episode1_id}/subtitles")
    assert len(still_listed.json()) == 1


@pytest.mark.asyncio
async def test_subtitle_generate_requires_shot_plan(client: httpx.AsyncClient) -> None:
    created = await client.post("/projects", json={"name": "Trial 01"})
    project_id = created.json()["id"]
    response = await client.post(f"/episodes/{project_id}/subtitles/generate")
    assert response.status_code == 409
