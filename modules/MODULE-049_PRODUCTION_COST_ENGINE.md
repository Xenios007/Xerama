# MODULE-049 — Production Cost Engine

**Status:** BUILD
**Depends on:** 031,041,044

## Objective
Measure true production economics, especially cost per accepted output.

## Requirements
- Persist provider/model/stage/project/episode/shot, usage, monetary cost, latency, attempts, accepted/rejected and failure reason.
- Calculate cost per accepted image, accepted video second and episode.
- Support unknown/free costs explicitly.
- Keep secrets/raw sensitive payloads out.

## Verification
Aggregation, retry-cost and free/unknown-cost tests.

## Done when
Provider decisions can be based on accepted-output economics rather than sticker price; commit/push.