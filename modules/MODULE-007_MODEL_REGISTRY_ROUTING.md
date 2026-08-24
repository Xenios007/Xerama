# MODULE-007 — Model Registry & Routing

**Status:** EXTEND
**Depends on:** 006

## Objective
Map logical AI roles to configurable models and support ranked fallback without hardcoded vendor assumptions.

## Requirements
- Registry for role, provider, model, capabilities, cost hints and priority.
- Support free-first profiles plus explicit pinned overrides.
- Validate compatibility with requested structured/vision capability.
- Record selected route on jobs/attempts when telemetry is enabled.
- Keep current model IDs replaceable.

## Verification
Routing, override, unavailable-model and fallback tests.

## Done when
Changing a model/provider requires configuration, not story-code edits; commit/push.