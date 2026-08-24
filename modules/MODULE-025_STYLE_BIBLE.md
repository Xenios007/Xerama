# MODULE-025 — Style Bible

**Status:** BUILD
**Depends on:** 004,012

## Objective
Create a persistent canonical visual language for each production.

## Requirements
- Persist textual style DNA, palette, lighting, temperature, texture, contrast, composition, negatives and canonical image asset ID.
- Support draft/approved/locked/version states.
- Expose style reference to prompt/QC systems.
- Do not require a real image provider for unit tests.

## Verification
Persistence, locking/versioning and reference-resolution tests.

## Done when
All visual generation can inherit one approved style anchor; commit/push.