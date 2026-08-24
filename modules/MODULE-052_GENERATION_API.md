# MODULE-052 — Generation API

**Status:** EXTEND
**Depends on:** 041,042,051

## Objective
Expose asynchronous generation controls for story and media stages.

## Requirements
- Start/regenerate/cancel supported project/episode/shot stages.
- Return job IDs immediately for long operations.
- Validate dependencies/locks and prevent duplicate incompatible runs.
- Keep synchronous dev path only where useful.

## Verification
Enqueue, duplicate prevention, cancel and dependency tests.

## Done when
Frontend can drive the full pipeline without blocking HTTP for media generation; commit/push.