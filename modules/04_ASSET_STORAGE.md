# Module 04 — Asset & Storage System

## Mission
Create the persistent media foundation before real image/video generation.

## Build
Define `Asset`, asset type/status, lineage/version/take metadata, hash, MIME/media metadata, provider/model/source references, project/episode/scene/shot ownership, acceptance/rejection and provenance fields. Implement `StorageProvider` and `LocalStorageProvider`; leave an S3-compatible contract for later.

Use content hashing where practical. Never treat temporary provider URLs as permanent. Support ingest from bytes/file/temp download, safe paths, deduplication, retrieval, deletion policy and orphan detection. Do not store large media blobs in SQLite.

Add asset APIs for list/detail/download metadata/accept/reject where appropriate.

## Tests
Storage path safety, hashing, dedupe, persistence, lineage, missing files, cleanup and repository round trips.

## Acceptance
Any future provider output can immediately become a durable Xerama asset with traceable lineage.

## Agent instructions
Follow ADR-020/022 and Wind Comic storage lessons. Use local storage for Trial 01. Add migration/tests/docs/changelog, run suite, commit, proceed to Module 05.