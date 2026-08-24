import pytest

from xerama.domain.asset import AssetOwnership, AssetProvenance, AssetStatus, AssetType
from xerama.repositories.sqlalchemy_impl import SQLAlchemyAssetRepository, SQLAlchemyProjectRepository


async def _project(session) -> str:
    project = await SQLAlchemyProjectRepository(session).create("p")
    await session.commit()
    return project.id


@pytest.mark.asyncio
async def test_create_and_get_round_trip(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyAssetRepository(session)
    asset = await repo.create(
        asset_type=AssetType.IMAGE,
        storage_path="ab/abc.png",
        content_hash="abc",
        ownership=AssetOwnership(project_id=project_id, episode_id="EP_1", shot_number=2),
        provenance=AssetProvenance(provider="fake", model="fake-image-v1"),
        mime_type="image/png",
        size_bytes=1024,
        width=1080,
        height=1920,
    )
    await session.commit()

    fetched = await repo.get(asset.id)
    assert fetched is not None
    assert fetched.storage_path == "ab/abc.png"
    assert fetched.ownership.episode_id == "EP_1"
    assert fetched.ownership.shot_number == 2
    assert fetched.provenance.provider == "fake"
    assert fetched.width == 1080 and fetched.height == 1920
    assert fetched.status == AssetStatus.PENDING


@pytest.mark.asyncio
async def test_get_by_hash(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyAssetRepository(session)
    await repo.create(
        asset_type=AssetType.IMAGE,
        storage_path="ab/abc.png",
        content_hash="hash-1",
        ownership=AssetOwnership(project_id=project_id),
    )
    await session.commit()

    found = await repo.get_by_hash("hash-1")
    assert found is not None
    assert await repo.get_by_hash("does-not-exist") is None


@pytest.mark.asyncio
async def test_list_by_ownership_filters(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyAssetRepository(session)
    await repo.create(
        asset_type=AssetType.IMAGE,
        storage_path="a.png",
        content_hash="h1",
        ownership=AssetOwnership(project_id=project_id, episode_id="EP_1"),
    )
    await repo.create(
        asset_type=AssetType.VIDEO,
        storage_path="b.mp4",
        content_hash="h2",
        ownership=AssetOwnership(project_id=project_id, episode_id="EP_2"),
    )
    await session.commit()

    all_for_project = await repo.list_by_ownership(project_id)
    assert len(all_for_project) == 2

    only_ep1 = await repo.list_by_ownership(project_id, episode_id="EP_1")
    assert len(only_ep1) == 1
    assert only_ep1[0].storage_path == "a.png"

    only_video = await repo.list_by_ownership(project_id, asset_type=AssetType.VIDEO)
    assert len(only_video) == 1
    assert only_video[0].storage_path == "b.mp4"


@pytest.mark.asyncio
async def test_set_status_accept_and_reject(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyAssetRepository(session)
    asset = await repo.create(
        asset_type=AssetType.IMAGE,
        storage_path="a.png",
        content_hash="h1",
        ownership=AssetOwnership(project_id=project_id),
    )
    await session.commit()

    accepted = await repo.set_status(asset.id, AssetStatus.ACCEPTED)
    assert accepted.status == AssetStatus.ACCEPTED

    rejected = await repo.set_status(asset.id, AssetStatus.REJECTED, rejection_reason="face drift")
    assert rejected.status == AssetStatus.REJECTED
    assert rejected.rejection_reason == "face drift"

    # Re-accepting clears any stale rejection reason.
    re_accepted = await repo.set_status(asset.id, AssetStatus.ACCEPTED)
    assert re_accepted.rejection_reason == ""


@pytest.mark.asyncio
async def test_delete_removes_row(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyAssetRepository(session)
    asset = await repo.create(
        asset_type=AssetType.IMAGE,
        storage_path="a.png",
        content_hash="h1",
        ownership=AssetOwnership(project_id=project_id),
    )
    await session.commit()

    await repo.delete(asset.id)
    await session.commit()
    assert await repo.get(asset.id) is None


@pytest.mark.asyncio
async def test_list_all(session) -> None:
    project_id = await _project(session)
    repo = SQLAlchemyAssetRepository(session)
    await repo.create(
        asset_type=AssetType.AUDIO,
        storage_path="a.wav",
        content_hash="h1",
        ownership=AssetOwnership(project_id=project_id),
    )
    await session.commit()
    assert len(await repo.list_all()) == 1
