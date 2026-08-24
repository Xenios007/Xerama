# MODULE-068 — Rate Limits / Abuse Protection

**Status:** BUILD/LATE
**Depends on:** 052,066,067

## Objective
Prevent accidental or malicious runaway generation and cost.

## Requirements
- Per-user/project/provider concurrency and request limits.
- Budget ceilings and duplicate-generation suppression.
- Clear 429/budget errors and retry guidance.
- Local trusted mode may use permissive defaults.

## Verification
Limit, concurrency, budget and reset-window tests.

## Done when
One client cannot unintentionally create unlimited expensive provider work; commit/push.