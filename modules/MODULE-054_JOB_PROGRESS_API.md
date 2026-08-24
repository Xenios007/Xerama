# MODULE-054 — Job / Progress API

**Status:** BUILD
**Depends on:** 041,050

## Objective
Expose production progress, attempts and failures to clients.

## Requirements
- List/get jobs by project/episode/stage/status.
- Return progress, attempts, error class/message and resulting asset IDs.
- Support polling first; optional SSE/WebSocket later if justified.
- Cancellation endpoint must respect job state.

## Verification
Progress/filter/cancel/error-shape tests.

## Done when
UI can render trustworthy live-ish production state from persisted jobs; commit/push.