import pytest

from xerama.domain.asset import AssetType
from xerama.pipeline.upload_validation import (
    UnsupportedContentTypeError,
    UploadTooLargeError,
    sanitize_extension,
    validate_upload,
)


def test_validate_upload_accepts_matching_content_type() -> None:
    validate_upload(AssetType.IMAGE, "image/png", size_bytes=100, max_size_bytes=1000)


def test_validate_upload_rejects_oversized_file() -> None:
    with pytest.raises(UploadTooLargeError):
        validate_upload(AssetType.IMAGE, "image/png", size_bytes=2000, max_size_bytes=1000)


def test_validate_upload_rejects_mismatched_content_type() -> None:
    with pytest.raises(UnsupportedContentTypeError):
        validate_upload(AssetType.IMAGE, "video/mp4", size_bytes=100, max_size_bytes=1000)


@pytest.mark.parametrize(
    "dangerous_type", ["text/html", "image/svg+xml", "application/javascript"]
)
def test_validate_upload_rejects_dangerous_content_types_for_any_asset_type(dangerous_type: str) -> None:
    with pytest.raises(UnsupportedContentTypeError):
        validate_upload(AssetType.OTHER, dangerous_type, size_bytes=100, max_size_bytes=1000)


def test_validate_upload_allows_empty_content_type() -> None:
    validate_upload(AssetType.IMAGE, "", size_bytes=100, max_size_bytes=1000)


def test_validate_upload_ignores_charset_suffix() -> None:
    validate_upload(AssetType.DOCUMENT, "text/plain; charset=utf-8", size_bytes=10, max_size_bytes=1000)


def test_validate_upload_other_asset_type_has_no_prefix_restriction() -> None:
    validate_upload(AssetType.OTHER, "application/zip", size_bytes=10, max_size_bytes=1000)


def test_sanitize_extension_keeps_plain_extension() -> None:
    assert sanitize_extension("frame.png") == ".png"


def test_sanitize_extension_lowercases() -> None:
    assert sanitize_extension("frame.PNG") == ".png"


def test_sanitize_extension_rejects_path_traversal_attempt() -> None:
    assert sanitize_extension("x.png/../../etc/passwd") == ""


def test_sanitize_extension_rejects_no_extension() -> None:
    assert sanitize_extension("noextension") == ""


def test_sanitize_extension_rejects_none_filename() -> None:
    assert sanitize_extension(None) == ""


def test_sanitize_extension_rejects_overly_long_extension() -> None:
    assert sanitize_extension("file." + "a" * 20) == ""
