"""MODULE-067 - hosted-mode authorization integration tests.

Exercises the full stack (real HTTP client -> FastAPI -> SQLAlchemy repos)
with `xerama_mode=hosted`, which is what actually turns on every
`authorize_project_access` check built for MODULE-067. All other API
tests (`test_api.py`) run in the default "standard" mode and must stay
green unaffected - that's verified separately, not here.
"""

import httpx
import pytest

from xerama.api.app import create_app
from xerama.config import ModelRoleRegistry, Settings, get_settings
from xerama.db.base import create_all, make_engine, make_session_factory
from xerama.domain.enums import ProjectRole
from xerama.pipeline.ai_gateway import AIGateway
from xerama.providers.fake import FakeLLMProvider
from xerama.providers.fake_frame_extractor import FakeFrameExtractor
from xerama.providers.fake_image import FakeImageProvider
from xerama.providers.fake_assembler import FakeAssembler
from xerama.providers.fake_lip_sync import FakeLipSyncProvider
from xerama.providers.fake_media_inspector import FakeMediaInspector
from xerama.providers.fake_media_qc import FakeMediaQCProvider
from xerama.providers.fake_video import FakeVideoProvider
from xerama.providers.fake_voice import FakeVoiceProvider
from xerama.providers.health import ProviderHealthTracker
from xerama.providers.local_storage import LocalStorageProvider
from xerama.repositories.sqlalchemy_impl import (
    SQLAlchemyProjectMembershipRepository,
    SQLAlchemyUserRepository,
)
from xerama.services.media_router import MediaProviderRouter


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("XERAMA_MODE", "hosted")
    get_settings.cache_clear()

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
    app.state.video_router = MediaProviderRouter([FakeVideoProvider()])
    app.state.frame_extractor = FakeFrameExtractor()
    app.state.voice_router = MediaProviderRouter([FakeVoiceProvider()])
    app.state.lip_sync_router = MediaProviderRouter([FakeLipSyncProvider()])
    app.state.media_qc_provider = FakeMediaQCProvider()
    app.state.episode_assembler = FakeAssembler()
    app.state.media_inspector = FakeMediaInspector()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.app = app
        yield ac

    await engine.dispose()
    get_settings.cache_clear()


async def _register_and_login(client: httpx.AsyncClient, email: str) -> str:
    registered = await client.post(
        "/auth/register", json={"email": email, "password": "correct horse battery"}
    )
    assert registered.status_code == 200, registered.text
    logged_in = await client.post(
        "/auth/login", json={"email": email, "password": "correct horse battery"}
    )
    assert logged_in.status_code == 200, logged_in.text
    return logged_in.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_register_login_me_logout_flow(client: httpx.AsyncClient) -> None:
    registered = await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": "correct horse battery"}
    )
    assert registered.status_code == 200
    assert registered.json()["email"] == "alice@example.com"
    assert "password" not in registered.json()
    assert "password_hash" not in registered.json()

    logged_in = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "correct horse battery"}
    )
    token = logged_in.json()["token"]

    me = await client.get("/auth/me", headers=_auth(token))
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"

    logged_out = await client.post("/auth/logout", headers=_auth(token))
    assert logged_out.status_code == 204

    after_logout = await client.get("/auth/me", headers=_auth(token))
    assert after_logout.status_code == 401


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(client: httpx.AsyncClient) -> None:
    await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": "correct horse battery"}
    )
    response = await client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "wrong password"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_project_requires_authentication(client: httpx.AsyncClient) -> None:
    response = await client.post("/projects", json={"name": "Trial 01"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_creator_becomes_owner_and_can_read_own_project(client: httpx.AsyncClient) -> None:
    token = await _register_and_login(client, "alice@example.com")
    created = await client.post("/projects", json={"name": "Trial 01"}, headers=_auth(token))
    assert created.status_code == 200
    project_id = created.json()["id"]

    fetched = await client.get(f"/projects/{project_id}", headers=_auth(token))
    assert fetched.status_code == 200
    assert fetched.json()["id"] == project_id


@pytest.mark.asyncio
async def test_unauthenticated_request_to_existing_project_is_401(client: httpx.AsyncClient) -> None:
    token = await _register_and_login(client, "alice@example.com")
    created = await client.post("/projects", json={"name": "Trial 01"}, headers=_auth(token))
    project_id = created.json()["id"]

    response = await client.get(f"/projects/{project_id}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_non_member_cannot_access_another_users_project(client: httpx.AsyncClient) -> None:
    """The core MODULE-067 "Done when" criterion: a hosted deployment
    cannot access another user's production through guessed IDs."""
    owner_token = await _register_and_login(client, "alice@example.com")
    created = await client.post("/projects", json={"name": "Trial 01"}, headers=_auth(owner_token))
    project_id = created.json()["id"]

    other_token = await _register_and_login(client, "bob@example.com")
    response = await client.get(f"/projects/{project_id}", headers=_auth(other_token))
    assert response.status_code == 403

    listed = await client.get("/projects", headers=_auth(other_token))
    assert listed.status_code == 200
    assert project_id not in [p["id"] for p in listed.json()]


@pytest.mark.asyncio
async def test_project_list_is_scoped_to_the_caller(client: httpx.AsyncClient) -> None:
    alice_token = await _register_and_login(client, "alice@example.com")
    await client.post("/projects", json={"name": "Alice's Project"}, headers=_auth(alice_token))

    bob_token = await _register_and_login(client, "bob@example.com")
    await client.post("/projects", json={"name": "Bob's Project"}, headers=_auth(bob_token))

    alice_list = await client.get("/projects", headers=_auth(alice_token))
    assert [p["name"] for p in alice_list.json()] == ["Alice's Project"]

    bob_list = await client.get("/projects", headers=_auth(bob_token))
    assert [p["name"] for p in bob_list.json()] == ["Bob's Project"]


@pytest.mark.asyncio
async def test_editor_role_cannot_archive_but_can_update(client: httpx.AsyncClient) -> None:
    owner_token = await _register_and_login(client, "alice@example.com")
    created = await client.post("/projects", json={"name": "Trial 01"}, headers=_auth(owner_token))
    project_id = created.json()["id"]

    editor_token = await _register_and_login(client, "carol@example.com")
    # Owner grants editor access via the auth service directly (no
    # project-invite endpoint exists yet - out of scope for MODULE-067,
    # see docs/IMPLEMENTATION_STATUS.md) - simulate it through the DB.
    session_factory = client.app.state.session_factory
    async with session_factory() as session:
        user_repo = SQLAlchemyUserRepository(session)
        carol = await user_repo.get_by_email("carol@example.com")
        membership_repo = SQLAlchemyProjectMembershipRepository(session)
        await membership_repo.grant(project_id, carol.id, ProjectRole.EDITOR)
        await session.commit()

    updated = await client.patch(
        f"/projects/{project_id}", json={"name": "Renamed"}, headers=_auth(editor_token)
    )
    assert updated.status_code == 200

    archived = await client.post(f"/projects/{project_id}/archive", headers=_auth(editor_token))
    assert archived.status_code == 403


@pytest.mark.asyncio
async def test_viewer_role_cannot_update(client: httpx.AsyncClient) -> None:
    owner_token = await _register_and_login(client, "alice@example.com")
    created = await client.post("/projects", json={"name": "Trial 01"}, headers=_auth(owner_token))
    project_id = created.json()["id"]

    viewer_token = await _register_and_login(client, "dave@example.com")
    session_factory = client.app.state.session_factory
    async with session_factory() as session:
        user_repo = SQLAlchemyUserRepository(session)
        dave = await user_repo.get_by_email("dave@example.com")
        membership_repo = SQLAlchemyProjectMembershipRepository(session)
        await membership_repo.grant(project_id, dave.id, ProjectRole.VIEWER)
        await session.commit()

    fetched = await client.get(f"/projects/{project_id}", headers=_auth(viewer_token))
    assert fetched.status_code == 200

    updated = await client.patch(
        f"/projects/{project_id}", json={"name": "Renamed"}, headers=_auth(viewer_token)
    )
    assert updated.status_code == 403


@pytest.mark.asyncio
async def test_non_member_cannot_upload_asset_to_anothers_project(client: httpx.AsyncClient) -> None:
    owner_token = await _register_and_login(client, "alice@example.com")
    created = await client.post("/projects", json={"name": "Trial 01"}, headers=_auth(owner_token))
    project_id = created.json()["id"]

    other_token = await _register_and_login(client, "bob@example.com")
    upload = await client.post(
        "/assets/upload",
        params={"project_id": project_id, "asset_type": "image"},
        files={"file": ("frame.png", b"fake png bytes", "image/png")},
        headers=_auth(other_token),
    )
    assert upload.status_code == 403


@pytest.mark.asyncio
async def test_invalid_bearer_token_is_treated_as_unauthenticated(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/projects", json={"name": "Trial 01"}, headers=_auth("not-a-real-token")
    )
    assert response.status_code == 401
