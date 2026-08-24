# MODULE-040 — Media Asset Storage

**Status:** BUILD
**Depends on:** 004,005

## Objective
Persist all generated/imported media under Xerama control rather than temporary provider URLs.

## Requirements
- StorageProvider abstraction and local implementation.
- Content hash, MIME/type, size, path, lineage, project/episode/scene/shot, take/version, provider/model and acceptance metadata.
- Safe atomic writes and collision handling.
- Future S3-compatible adapter boundary.

## Verification
Store/read/hash/dedup/delete-policy and restart tests using temp directories.

## Done when
Every media module can reference stable asset IDs and local files survive provider URL expiry; commit/push.