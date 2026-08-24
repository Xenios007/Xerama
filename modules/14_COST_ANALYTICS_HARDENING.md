# Module 14 — Cost, Analytics & Production Hardening

## Mission
Close the gap between a working demo and a measurable production system.

## Build
Reintroduce per-call telemetry at the existing AI/media gateway choke points despite the temporary XER-001 deviation. Record logical role/stage, provider/model, latency, usage where available, estimated/actual cost, attempts, accepted/rejected, QC scores and rejection reason. Never log secrets or sensitive raw credentials.

Compute cost per accepted image, accepted video second and accepted episode. Add provider/model benchmark summaries and policy inputs for routing without creating an opaque self-modifying system.

Add production hardening: health/readiness endpoints, structured logging, request/job correlation IDs, configuration validation, DB backup/export guidance, storage integrity scan, rate/concurrency limits, security review of file paths/uploads/CORS/secrets, CI workflow, lint/type/test gates and release checklist.

Create analytics schema/interfaces for future performance signals (3-second retention, watch time, completion, rewatch, drop points, shares, continuation) without requiring platform integrations now.

## Tests
Telemetry accuracy, no-secret logging, cost aggregation, accepted-output metrics, integrity checks, config failures, CI commands and security regression cases.

## Acceptance
Trial 01 can report what every episode cost, which providers/models caused retries, cost per accepted output, QC outcomes and system health; the repository has a repeatable CI/release path.

## Agent instructions
Read the telemetry deviation in `docs/IMPLEMENTATION_STATUS.md` and ADR-010/024. Implement additively. Update architecture/status/changelog/README, run all backend and frontend checks, commit, then produce `docs/FINAL_SYSTEM_AUDIT.md` listing remaining gaps before calling Xerama production-complete.