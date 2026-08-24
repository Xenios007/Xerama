# MODULE-062 — Retention Analytics

**Status:** BUILD
**Depends on:** 061

## Objective
Analyze viewer retention in terms useful to microdrama production.

## Requirements
- Compute available 3-second retention, average watch time, completion, drop points, rewatch and episode continuation.
- Normalize carefully when source platforms expose different metrics.
- Link drop regions to episode timeline/shots where timestamps exist.
- Avoid inventing unavailable metrics.

## Verification
Metric calculation and missing-data tests.

## Done when
The system can summarize where an episode retained/lost viewers with source-aware confidence; commit/push.