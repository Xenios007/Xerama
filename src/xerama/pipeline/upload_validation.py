"""Manual-upload validation (MODULE-066 - Security).

`AssetService.ingest_bytes` and `LocalStorageProvider` already guard
against path traversal at the storage layer (ADR-022 - content-addressed
paths, `_safe_path` resolves+checks against the storage root). This
module covers the two checks that must happen *before* an untrusted
upload reaches that layer: the declared size never exceeds a configured
ceiling, and the declared content type is plausible for the declared
`AssetType` - in particular, a browser-executable content type
(`text/html`, `image/svg+xml`, ...) must never be accepted, since
`GET /assets/{id}/download` echoes the stored `mime_type` back verbatim
as the response `Content-Type` (ADR-020's "durable Xerama asset" is not
a promise to also be a safe redistribution channel for whatever a
client claims a file is).
"""

from xerama.domain.asset import AssetType


class UploadValidationError(ValueError):
    """Base class for a rejected manual upload."""


class UploadTooLargeError(UploadValidationError):
    pass


class UnsupportedContentTypeError(UploadValidationError):
    pass


# Content types that must never be persisted with their claimed type,
# regardless of declared AssetType - browsers execute these when served
# back, turning `download_asset` into a stored-XSS vector.
_DANGEROUS_CONTENT_TYPES = frozenset(
    {
        "text/html",
        "application/xhtml+xml",
        "image/svg+xml",
        "application/javascript",
        "text/javascript",
        "application/x-msdownload",
    }
)

# Per-AssetType allow-list, matched by prefix. AssetType.OTHER has none -
# it exists precisely for un-typed content - but is still subject to the
# dangerous-content-type denylist above.
_ALLOWED_CONTENT_TYPE_PREFIXES: dict[AssetType, tuple[str, ...]] = {
    AssetType.IMAGE: ("image/",),
    AssetType.VIDEO: ("video/",),
    AssetType.AUDIO: ("audio/",),
    AssetType.SUBTITLE: ("text/plain", "text/vtt", "application/x-subrip"),
    AssetType.DOCUMENT: ("application/pdf", "text/plain", "application/json"),
}


def validate_upload(
    asset_type: AssetType, content_type: str, size_bytes: int, max_size_bytes: int
) -> None:
    if size_bytes > max_size_bytes:
        raise UploadTooLargeError(
            f"upload of {size_bytes} bytes exceeds the {max_size_bytes} byte limit"
        )

    normalized = content_type.split(";", 1)[0].strip().lower()
    if not normalized:
        return  # no Content-Type sent - falls back to application/octet-stream on download, safe.

    if normalized in _DANGEROUS_CONTENT_TYPES:
        raise UnsupportedContentTypeError(f"content type {content_type!r} is not permitted")

    allowed_prefixes = _ALLOWED_CONTENT_TYPE_PREFIXES.get(asset_type)
    if allowed_prefixes and not any(normalized.startswith(p) for p in allowed_prefixes):
        raise UnsupportedContentTypeError(
            f"content type {content_type!r} does not match declared asset type {asset_type.value!r}"
        )


def sanitize_extension(filename: str | None) -> str:
    """Extracts a safe storage-path suffix from a client-supplied filename.

    Only a plain alphanumeric extension is trusted; anything else
    (path separators, `..`, control characters, no extension at all)
    degrades to no extension rather than being embedded in the
    content-addressed storage path - `LocalStorageProvider` would reject
    a traversal attempt outright, but there is no reason to carry
    untrusted bytes into a filesystem path at all when a safe default
    exists.
    """
    if not filename or "." not in filename:
        return ""
    candidate = filename.rsplit(".", 1)[-1]
    if 1 <= len(candidate) <= 10 and candidate.isalnum():
        return "." + candidate.lower()
    return ""
