# MODULE-042 — Worker Architecture

**Status:** BUILD
**Depends on:** 041

## Objective
Execute queued LLM/image/video/audio/render jobs outside request handlers.

## Requirements
- Local worker process with stage-handler registry.
- Graceful shutdown, heartbeat/lease, concurrency limits and per-provider limits.
- Idempotent handlers where practical.
- Keep interface replaceable by Redis/Celery/RQ later.

## Verification
Worker lifecycle, concurrency, crash/reclaim and handler tests.

## Done when
API can enqueue production and workers can finish it independently; commit/push.