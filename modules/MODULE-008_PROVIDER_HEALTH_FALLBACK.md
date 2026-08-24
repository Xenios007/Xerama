# MODULE-008 — Provider Health / Fallback

**Status:** EXTEND
**Depends on:** 007

## Objective
Prevent repeated calls to unhealthy providers and automatically choose safe fallbacks.

## Requirements
- Extend ProviderHealthTracker to per-provider/model state.
- Track auth, quota, rate limit, saturation, timeout and transient failures.
- Implement configurable circuit open/cooldown/recovery behavior.
- Never retry non-retriable invalid requests blindly.
- Surface route/fallback reason for inspection.

## Verification
Deterministic circuit-breaker and recovery tests with fake clock/provider.

## Done when
Provider failure cannot stall the entire pipeline when an eligible fallback exists; commit/push.