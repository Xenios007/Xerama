import httpx
import pytest
import respx

from xerama.domain.asset import AssetOwnership, AssetProvenance, AssetStatus, AssetType
from xerama.providers.local_storage import LocalStorageProvider
from xerama.repositories.sqlalchemy_impl import SQLAlchemyAssetRepository, SQLAlchemyProjectRepository
from xerama.services.asset_service import AssetService


@pytest.fixture
def storage(tmp_path):
    return LocalStorageProvider(tmp_path / "store")


async def _project(session) -> str:
    project = await SQLAlchemyProjectRepository(session).create("p")
    await session.commit()
    return project.id


def _service(session, storage) -> AssetService:
    return AssetService(storage=storage, asset_repo=SQLAlchemyAssetRepository(session))


@pytest.mark.asyncio
async def test_ingest_bytes_persists_and_hashes(session, storage) -> None:
    project_id = await _project(session)
    service = _service(session, storage)
    asset = await service.ingest_bytes(
        b"fake image bytes",
        AssetType.IMAGE,
        AssetOwnership(project_id=project_id),
        provenance=AssetProvenance(provider="fake", model="fake-image-v1"),
        mime_type="image/png",
        ext=".png",
    )
    await session.commit()

    assert asset.content_hash  # sha256 hex digest, non-empty
    assert asset.size_bytes == len(b"fake image bytes")
    assert await storage.read_bytes(asset.storage_path) == b"fake image bytes"


@pytest.mark.asyncio
async def test_ingest_dedupes_disk_write_but_creates_new_asset_row(session, storage) -> None:
    project_id = await _project(session)
    service = _service(session, storage)

    first = await service.ingest_bytes(b"same bytes", AssetType.IMAGE, AssetOwnership(project_id=project_id))
    second = await service.ingest_bytes(b"same bytes", AssetType.IMAGE, AssetOwnership(project_id=project_id))
    await session.commit()

    assert first.id != second.id
    assert first.storage_path == second.storage_path
    assert first.content_hash == second.content_hash


@pytest.mark.asyncio
async def test_ingest_from_url_downloads_and_records_source_url(session, storage) -> None:
    project_id = await _project(session)
    service = _service(session, storage)

    with respx.mock(assert_all_called=True) as mock:
        mock.get("https://provider.example/output.png").mock(
            return_value=httpx.Response(200, content=b"remote bytes", headers={"content-type": "image/png"})
        )
        async with httpx.AsyncClient() as client:
            asset = await service.ingest_from_url(
                "https://provider.example/output.png",
                client,
                AssetType.IMAGE,
                AssetOwnership(project_id=project_id),
                ext=".png",
            )
    await session.commit()

    assert asset.mime_type == "image/png"
    assert asset.provenance.source_url == "https://provider.example/output.png"
    assert await storage.read_bytes(asset.storage_path) == b"remote bytes"


@pytest.mark.asyncio
async def test_accept_and_reject(session, storage) -> None:
    project_id = await _project(session)
    service = _service(session, storage)
    asset = await service.ingest_bytes(b"x", AssetType.IMAGE, AssetOwnership(project_id=project_id))
    await session.commit()

    accepted = await service.accept(asset.id)
    assert accepted.status == AssetStatus.ACCEPTED

    rejected = await service.reject(asset.id, "bad hands")
    assert rejected.status == AssetStatus.REJECTED
    assert rejected.rejection_reason == "bad hands"


@pytest.mark.asyncio
async def test_delete_protects_accepted_assets_unless_forced(session, storage) -> None:
    project_id = await _project(session)
    service = _service(session, storage)
    asset = await service.ingest_bytes(b"x", AssetType.IMAGE, AssetOwnership(project_id=project_id))
    await session.commit()
    await service.accept(asset.id)
    await session.commit()

    with pytest.raises(PermissionError):
        await service.delete(asset.id)

    await service.delete(asset.id, force=True)
    await session.commit()
    assert await service.get(asset.id) is None


@pytest.mark.asyncio
async def test_delete_keeps_file_while_another_asset_shares_its_hash(session, storage) -> None:
    project_id = await _project(session)
    service = _service(session, storage)
    first = await service.ingest_bytes(b"shared", AssetType.IMAGE, AssetOwnership(project_id=project_id))
    second = await service.ingest_bytes(b"shared", AssetType.IMAGE, AssetOwnership(project_id=project_id))
    await session.commit()

    await service.delete(first.id)
    await session.commit()
    assert await storage.exists(second.storage_path)  # still referenced by `second`

    await service.delete(second.id)
    await session.commit()
    assert not await storage.exists(second.storage_path)  # last reference gone


@pytest.mark.asyncio
async def test_find_missing_files_detects_deleted_backing_file(session, storage) -> None:
    project_id = await _project(session)
    service = _service(session, storage)
    asset = await service.ingest_bytes(b"x", AssetType.IMAGE, AssetOwnership(project_id=project_id))
    await session.commit()

    await storage.delete(asset.storage_path)  # simulate file loss without touching the DB row

    missing = await service.find_missing_files()
    assert [a.id for a in missing] == [asset.id]


@pytest.mark.asyncio
async def test_find_unreferenced_files_detects_orphaned_disk_files(session, storage) -> None:
    project_id = await _project(session)
    service = _service(session, storage)
    await service.ingest_bytes(b"tracked", AssetType.IMAGE, AssetOwnership(project_id=project_id))
    await session.commit()

    await storage.save_bytes(b"stray file nobody references", "zz/stray.bin")

    unreferenced = await service.find_unreferenced_files()
    assert unreferenced == ["zz/stray.bin"]
