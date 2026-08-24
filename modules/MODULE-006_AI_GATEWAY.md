# MODULE-006 — AI Gateway

**Status:** AUDIT/EXTEND
**Depends on:** 002,003

## Objective
Provide one robust structured-generation entry point for text/LLM tasks.

## Requirements
- Preserve existing OpenRouter and FakeLLM support.
- Enforce role-based configuration, structured schemas, timeouts, retries and repair.
- Classify provider errors consistently.
- Support cancellation and request metadata.
- Do not expose provider payloads to story services.

## Verification
Mocked success, invalid JSON repair, timeout, rate limit, auth, quota and cancellation tests; no paid calls.

## Done when
Every text AI stage uses the gateway rather than direct HTTP/provider calls; full suite passes; commit/push.