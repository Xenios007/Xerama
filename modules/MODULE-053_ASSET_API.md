# MODULE-053 — Asset API

**Status:** BUILD
**Depends on:** 040,051

## Objective
Expose secure metadata/preview/download/import controls for production assets.

## Requirements
- List/filter/get asset metadata and versions/takes.
- Serve local assets safely without path traversal.
- Approve/reject/lock where authorized.
- Import user reference assets with validation/provenance metadata.

## Verification
Path safety, filtering, lifecycle and upload validation tests.

## Done when
Frontend can inspect and manage assets without filesystem access; commit/push.