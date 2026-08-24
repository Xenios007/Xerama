# MODULE-031 — Media Provider Router

**Status:** BUILD
**Depends on:** 002,008

## Objective
Route image/video/audio/media tasks by capability, health, policy and later cost/quality history.

## Requirements
- Provider registry with typed capabilities and limits.
- Filter incompatible/unhealthy providers before calls.
- Rank preferred/fallback providers by configurable policy.
- Support fake providers for every media class.
- Record routing reason on generation attempts.

## Verification
Capability filtering, health fallback and no-eligible-provider tests.

## Done when
Production services request capabilities rather than vendor names; commit/push.