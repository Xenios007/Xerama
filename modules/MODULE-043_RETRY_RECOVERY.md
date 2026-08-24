# MODULE-043 — Retry / Recovery

**Status:** BUILD
**Depends on:** 008,041,042

## Objective
Make failures recoverable without duplicating accepted work or restarting whole productions.

## Requirements
- Error-class-specific retry policy with bounded attempts/backoff.
- Resume pipeline from persisted successful artifacts.
- Idempotency keys for expensive operations where feasible.
- Dead-letter/blocked state and operator-visible reason.

## Verification
Transient/permanent failure, restart-resume and duplicate-prevention tests.

## Done when
A process/provider failure can resume safely from the last durable checkpoint; commit/push.