# Xerama Architecture Decision Log

This file records important early decisions so future implementation does not accidentally reverse them without discussion.

## ADR-001 — Python-first backend

**Status:** Proposed / initial default

Xerama's AI orchestration backend will initially be designed around Python because of its AI ecosystem, async API support, schema-validation libraries, media tooling, and rapid experimentation workflow.

The architecture should still expose APIs so the eventual frontend is independent of the backend language.

## ADR-002 — OpenRouter as initial LLM gateway

**Status:** Accepted for V1

OpenRouter will be the first external LLM gateway. Xerama will not expose OpenRouter-specific assumptions throughout story logic; provider interaction belongs behind a model gateway.

## ADR-003 — Minimum two candidates in Standard mode

**Status:** Accepted

Standard creative generation produces at least two independent candidates. A judge selects A, B, or MERGE.

Fast mode may use one candidate. Quality mode may use three or more.

## ADR-004 — Model IDs are configuration

**Status:** Accepted

Model IDs must not be scattered through business logic. Logical roles map to configured providers/models.

Reason: model availability, price, limits, and quality change quickly.

## ADR-005 — Canonical state is authoritative

**Status:** Accepted

LLM conversation memory is not the source of truth for a series. Approved canonical state is persisted and explicitly supplied to models as required.

## ADR-006 — Generated output is not automatically canon

**Status:** Accepted

AI output is a proposal until schema, continuity, and applicable quality validations pass.

## ADR-007 — Structured output first

**Status:** Accepted

Core AI stages should return schema-valid structured data where possible. Prose remains appropriate for final creative artifacts such as dialogue, but metadata and state changes remain structured.

## ADR-008 — Story validation precedes media spending

**Status:** Accepted

Xerama will prove and validate story-level quality before invoking expensive image/video generation.

## ADR-009 — Media providers are adapters

**Status:** Planned

Image, video, voice, music, and related providers should implement common Xerama interfaces so providers can be replaced or routed per shot/task.

## ADR-010 — Preserve raw AI telemetry

**Status:** Planned

For benchmarkability, retain enough metadata to reconstruct AI decisions:

- logical role
- provider/model
- prompt/schema version
- generation parameters
- raw response
- parsed response
- token usage when available
- latency
- retries
- validation errors
- final acceptance/rejection

Secrets and credentials must never be included in logs.
