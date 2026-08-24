# MODULE-002 — Configuration & Environment

**Status:** AUDIT/EXTEND
**Depends on:** 001

## Objective
Make all runtime configuration typed, validated, environment-driven, and safe for local/test/production modes.

## Requirements
- Audit existing Settings/ModelRoleRegistry.
- Centralize DB, storage, provider, model, worker, FFmpeg, frontend/CORS and logging settings.
- Provide `.env.example` with placeholders only.
- Never log or commit secrets.
- Fail clearly for required configuration while allowing fake providers in tests.

## Verification
Tests for defaults, env overrides, invalid values and secret redaction.

## Done when
No business logic contains environment lookups or hardcoded credentials/model assumptions; full tests pass; docs/status updated; commit/push.