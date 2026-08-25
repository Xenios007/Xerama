"""MODULE-075 - one deterministic, no-paid-API end-to-end production
test: brief -> concept -> canon -> scripts -> shots -> fake media -> QC
-> audio/subtitles -> render/export -> reopen-after-restart.

Run with `pytest -m e2e` (see docs/TESTING.md). Every provider is fake
(`FakeLLMProvider`/`FakeImageProvider`/`FakeVideoProvider`/
`FakeVoiceProvider`/`FakeMediaQCProvider`/`FakeAssembler`/
`FakeMediaInspector`) - "no paid API dependency in default E2E" is
satisfied by construction, not by skipping anything.
"""

import json

import httpx
import pytest

import fixtures as fx
from xerama.api.app import create_app
from xerama.config import ModelRoleRegistry, Settings
from xerama.db.base import create_all, make_engine, make_session_factory
from xerama.pipeline.ai_gateway import AIGateway
from xerama.pipeline.rate_limiting import RateLimiter
from xerama.providers.fake import FakeLLMProvider
from xerama.providers.fake_assembler import FakeAssembler
from xerama.providers.fake_frame_extractor import FakeFrameExtractor
from xerama.providers.fake_image import FakeImageProvider
from xerama.providers.fake_lip_sync import FakeLipSyncProvider
from xerama.providers.fake_media_inspector import FakeMediaInspector
from xerama.providers.fake_media_qc import FakeMediaQCProvider
from xerama.providers.fake_video import FakeVideoProvider
from xerama.providers.fake_voice import FakeVoiceProvider
from xerama.providers.health import ProviderHealthTracker
from xerama.providers.local_storage import LocalStorageProvider
from xerama.services.media_router import MediaProviderRouter

pytestmark = pytest.mark.e2e


def _build_app(db_path, storage_path, llm_responses=()):
    app = create_app()
    engine = make_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = make_session_factory(engine)
    provider = FakeLLMProvider(list(llm_responses))
    gateway = AIGateway(provider=provider, roles=ModelRoleRegistry(Settings()), health=ProviderHealthTracker())

    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.ai_gateway = gateway
    app.state.storage_provider = LocalStorageProvider(storage_path)
    app.state.image_router = MediaProviderRouter([FakeImageProvider()])
    app.state.video_router = MediaProviderRouter([FakeVideoProvider()])
    app.state.voice_router = MediaProviderRouter([FakeVoiceProvider()])
    app.state.lip_sync_router = MediaProviderRouter([FakeLipSyncProvider()])
    app.state.frame_extractor = FakeFrameExtractor()
    app.state.media_qc_provider = FakeMediaQCProvider()
    app.state.episode_assembler = FakeAssembler()
    app.state.media_inspector = FakeMediaInspector()
    app.state.rate_limiter = RateLimiter(
        requests_per_window=1000, window_seconds=60.0, max_concurrent_per_project=1000
    )
    return app, engine, provider


@pytest.mark.asyncio
async def test_full_production_flow_survives_a_restart(tmp_path) -> None:
    db_path = tmp_path / "e2e.db"
    storage_path = tmp_path / "storage"

    app, engine, provider = _build_app(
        db_path,
        storage_path,
        llm_responses=[
            json.dumps(fx.concept("A")),
            json.dumps(fx.concept("B")),
            json.dumps(fx.judge_result("A")),
            json.dumps(fx.bible()),
            json.dumps(fx.cast()),
            json.dumps(fx.season_plan()),
            json.dumps(fx.outline_set(3)),
            json.dumps(fx.script()),
            json.dumps(fx.shot_plan()),
        ],
    )
    await create_all(engine)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Seed the project and run concept -> judge -> canon -> scripts
        #    -> shots (Showrunner.run - MODULE-009-020).
        created = await client.post("/projects", json={"name": "E2E Trial 01"})
        project_id = created.json()["id"]

        generated = await client.post(
            f"/projects/{project_id}/generate-series",
            json={"genre": "thriller", "episode_count": 3, "episode_duration_seconds": 75},
        )
        assert generated.status_code == 200, generated.text
        result = generated.json()
        series_id = result["series_id"]
        episode1_id = result["episode1_id"]
        assert len(result["outlines"]) == 3  # "one small 3-episode project"

        # 2. Fake media: image keyframe -> QC -> accept (MODULE-029/044).
        storyboard = (
            await client.post(f"/episodes/{episode1_id}/scenes/1/shots/1/storyboard")
        ).json()
        keyframe = (
            await client.post(f"/storyboards/{storyboard['id']}/keyframes/generate")
        ).json()
        assert keyframe["status"] == "pending"
        accepted_storyboard = await client.post(
            f"/storyboards/{storyboard['id']}/keyframes/{keyframe['id']}/accept"
        )
        assert accepted_storyboard.status_code == 200, accepted_storyboard.text
        assert accepted_storyboard.json()["status"] == "approved"

        # 3. Fake media: video take -> QC -> accept (MODULE-032/044).
        video_production = (
            await client.post(f"/episodes/{episode1_id}/scenes/1/shots/1/video-production")
        ).json()
        take = (
            await client.post(f"/video-productions/{video_production['id']}/takes/generate")
        ).json()
        accepted_take = await client.post(
            f"/video-productions/{video_production['id']}/takes/{take['id']}/accept"
        )
        assert accepted_take.status_code == 200, accepted_take.text
        assert accepted_take.json()["status"] == "approved"

        # 4. Fake media: dialogue audio take -> QC -> accept (MODULE-034/035/044).
        audio_production = (
            await client.post(f"/episodes/{episode1_id}/scenes/1/shots/1/audio-production")
        ).json()
        dialogue_take = (
            await client.post(
                f"/audio-productions/{audio_production['id']}/takes/generate",
                json={"character_id": "CHAR_001"},
            )
        ).json()
        accepted_dialogue = await client.post(
            f"/audio-productions/{audio_production['id']}/takes/{dialogue_take['id']}/accept"
        )
        assert accepted_dialogue.status_code == 200, accepted_dialogue.text

        # 5. Subtitles (MODULE-039).
        subtitles = await client.post(f"/episodes/{episode1_id}/subtitles/generate")
        assert subtitles.status_code == 200, subtitles.text
        assert len(subtitles.json()) >= 1

        # 6. Render + approve (MODULE-046/047), then export at the
        #    vertical profile and validate (MODULE-048) - export builds
        #    its own render version, so the "final" approved version is
        #    whichever one is approved last, not necessarily render v1.
        render_asset = await client.post(f"/episodes/{episode1_id}/render")
        assert render_asset.status_code == 200, render_asset.text

        renders = (await client.get(f"/episodes/{episode1_id}/renders")).json()
        render_id = renders[0]["id"]
        approve = await client.post(f"/episode-renders/{render_id}/approve")
        assert approve.status_code == 200
        assert approve.json()["status"] == "approved"

        export = await client.post(f"/episodes/{episode1_id}/export")
        assert export.status_code == 200, export.text
        export_body = export.json()
        assert export_body["asset"]["type"] == "video"
        assert export_body["validation"]["gate"] == "vertical_export"
        assert export_body["validation"]["status"] in ("pass", "warn", "block")

        export_render_id = export_body["render"]["id"]
        approve_export = await client.post(f"/episode-renders/{export_render_id}/approve")
        assert approve_export.status_code == 200
        assert approve_export.json()["status"] == "approved"
        render_id = export_render_id  # the final approved version, checked after restart below

        assert provider.calls  # the fake LLM queue was actually consumed, not bypassed

    await engine.dispose()

    # 7. "Reopen project after restart" - a brand-new app/engine/client
    #    pointed at the exact same DB file and asset storage directory,
    #    matching how a real process restart reconnects (same technique
    #    as MODULE-074's fresh-session boundary tests, at the whole-app
    #    level instead of just a new SQLAlchemy session).
    restarted_app, restarted_engine, _ = _build_app(db_path, storage_path)
    restarted_transport = httpx.ASGITransport(app=restarted_app)
    async with httpx.AsyncClient(transport=restarted_transport, base_url="http://test") as client:
        project = await client.get(f"/projects/{project_id}")
        assert project.status_code == 200
        assert project.json()["name"] == "E2E Trial 01"

        episodes = await client.get(f"/series/{series_id}/episodes")
        assert len(episodes.json()) == 3

        current_render = await client.get(f"/episodes/{episode1_id}/renders/current")
        assert current_render.status_code == 200
        assert current_render.json()["id"] == render_id
        assert current_render.json()["status"] == "approved"

        reopened_subtitles = await client.get(f"/episodes/{episode1_id}/subtitles")
        assert len(reopened_subtitles.json()) >= 1

        reopened_storyboard = await client.get(f"/storyboards/{storyboard['id']}")
        assert reopened_storyboard.json()["status"] == "approved"

        # The final exported episode asset's actual bytes are still
        # readable from disk after "restart" too - not just the DB row.
        downloaded = await client.get(f"/assets/{current_render.json()['render_asset_id']}/download")
        assert downloaded.status_code == 200
        assert len(downloaded.content) > 0

    await restarted_engine.dispose()
