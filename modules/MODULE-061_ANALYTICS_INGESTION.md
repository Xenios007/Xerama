# MODULE-061 — Analytics Ingestion

**Status:** BUILD
**Depends on:** 047,049

## Objective
Create provider/platform-neutral ingestion for post-publication performance metrics.

## Requirements
- Define episode/version metric schema with source and observation window.
- Support manual/import adapter first; platform APIs later.
- Store impressions/views, watch metrics, engagement and continuation where available.
- Preserve raw-source provenance and normalized values.

## Verification
Import, deduplication, normalization and version-association tests.

## Done when
Performance data can be attached reliably to the exact published episode version; commit/push.