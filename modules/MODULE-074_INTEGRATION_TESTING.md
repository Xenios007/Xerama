# MODULE-074 — Integration Testing

**Status:** BUILD
**Depends on:** 071

## Objective
Verify boundaries between API, DB, queue, workers, storage, providers and editor.

## Requirements
- Test story pipeline through persistence.
- Test queued fake media generation through asset/QC lifecycle.
- Test API-worker restart/resume behavior.
- Test FFmpeg integration conditionally when installed.

## Verification
Dedicated integration test command documented and CI-safe.

## Done when
Major subsystem interfaces are exercised together, not only in isolated unit tests; commit/push.