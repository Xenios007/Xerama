# MODULE-076 — Failure Simulation

**Status:** BUILD
**Depends on:** 043,074

## Objective
Prove recovery behavior under realistic provider/process/storage failures.

## Requirements
- Simulate timeout, rate limit, quota, corrupt media, worker crash, restart, unavailable provider and failed QC.
- Verify fallback/retry budgets and no duplicate accepted assets.
- Verify unrecoverable jobs become inspectable rather than hanging.

## Verification
Automated failure matrix using fake providers/fault injection.

## Done when
Expected failure classes have tested recovery or explicit terminal behavior; commit/push.