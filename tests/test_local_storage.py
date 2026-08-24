import pytest

from xerama.providers.local_storage import LocalStorageProvider, UnsafeStoragePathError


@pytest.fixture
def storage(tmp_path):
    return LocalStorageProvider(tmp_path / "store")


@pytest.mark.asyncio
async def test_save_and_read_bytes_round_trip(storage) -> None:
    saved_path = await storage.save_bytes(b"hello world", "ab/abc123.bin")
    assert saved_path == "ab/abc123.bin"
    assert await storage.exists("ab/abc123.bin")
    assert await storage.read_bytes("ab/abc123.bin") == b"hello world"


@pytest.mark.asyncio
async def test_save_creates_parent_directories(storage) -> None:
    await storage.save_bytes(b"data", "deep/nested/dir/file.bin")
    assert await storage.exists("deep/nested/dir/file.bin")


@pytest.mark.asyncio
async def test_read_missing_file_raises(storage) -> None:
    with pytest.raises(FileNotFoundError):
        await storage.read_bytes("does/not/exist.bin")


@pytest.mark.asyncio
async def test_exists_false_for_missing_file(storage) -> None:
    assert await storage.exists("nope.bin") is False


@pytest.mark.asyncio
async def test_delete_removes_file(storage) -> None:
    await storage.save_bytes(b"data", "a/b.bin")
    await storage.delete("a/b.bin")
    assert await storage.exists("a/b.bin") is False


@pytest.mark.asyncio
async def test_delete_missing_file_is_a_no_op(storage) -> None:
    await storage.delete("never/existed.bin")  # must not raise


@pytest.mark.asyncio
async def test_save_file_from_local_path(storage, tmp_path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"source bytes")
    await storage.save_file(str(source), "copied.bin")
    assert await storage.read_bytes("copied.bin") == b"source bytes"


@pytest.mark.asyncio
async def test_list_all_returns_forward_slash_relative_paths(storage) -> None:
    await storage.save_bytes(b"1", "a/b/c.bin")
    await storage.save_bytes(b"2", "x.bin")
    paths = set(await storage.list_all())
    assert paths == {"a/b/c.bin", "x.bin"}


@pytest.mark.asyncio
async def test_path_traversal_is_rejected(storage) -> None:
    with pytest.raises(UnsafeStoragePathError):
        await storage.save_bytes(b"evil", "../../../etc/passwd")


@pytest.mark.asyncio
async def test_absolute_path_traversal_is_rejected(storage) -> None:
    with pytest.raises(UnsafeStoragePathError):
        await storage.save_bytes(b"evil", "/etc/passwd")


@pytest.mark.asyncio
async def test_exists_returns_false_rather_than_raising_for_unsafe_path(storage) -> None:
    assert await storage.exists("../outside.bin") is False


def test_absolute_path_stays_within_root(storage) -> None:
    resolved = storage.absolute_path("a/b.bin")
    assert str(resolved).startswith(str(storage.absolute_path(".")))
