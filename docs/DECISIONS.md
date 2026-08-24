# Xerama Architecture Decision Log

This file records important early decisions so future implementation does not accidentally reverse them without discussion.

## ADR-001 — Python-first backend

**Status:** Accepted / initial default

Xerama's AI orchestration backend will initially be designed around Python because of its AI ecosystem, async API support, schema-validation libraries, media tooling and rapid experimentation workflow.

The architecture should still expose APIs so the eventual frontend is independent of the backend language.

## ADR-002 — OpenRouter as initial LLM gateway

**Status:** Accepted for V1

OpenRouter will be the first external LLM gateway. Xerama will not expose OpenRouter-specific assumptions throughout story logic; provider interaction belongs behind a model gateway.

## ADR-003 — Minimum two candidates in Standard mode

**Status:** Accepted

Standard creative generation produces at least two independent candidates. A judge selects A, B or MERGE.

Fast mode may use one candidate. Quality mode may use three or more.

## ADR-004 — Model IDs are configuration

**Status:** Accepted

Model IDs must not be scattered through business logic. Logical roles map to configured providers/models.

Reason: model availability, price, limits and quality change quickly.

## ADR-005 — Canonical state is authoritative

**Status:** Accepted

LLM conversation memory is not the source of truth for a series. Approved canonical state is persisted and explicitly supplied to models as required.

## ADR-006 — Generated output is not automatically canon

**Status:** Accepted

AI output is a proposal until schema, continuity and applicable quality validations pass.

## ADR-007 — Structured output first

**Status:** Accepted

Core AI stages should return schema-valid structured data where possible. Prose remains appropriate for final creative artifacts such as dialogue, but metadata and state changes remain structured.

## ADR-008 — Story validation precedes media spending

**Status:** Accepted

Xerama will prove and validate story-level quality before invoking expensive image/video generation. Hook, pacing, cliffhanger, continuity and feasibility checks should run before media spending where possible.

## ADR-009 — Media providers are capability-bearing adapters

**Status:** Accepted

Image, video, voice, lip-sync, music and related providers implement common Xerama interfaces. Adapters advertise capabilities and limits; routing selects an eligible provider per shot/task.

This decision is reinforced by source-level study of Wind Comic.

## ADR-010 — Preserve raw AI telemetry

**Status:** Accepted

For benchmarkability, retain enough metadata to reconstruct AI decisions:

- logical role;
- provider/model;
- prompt/schema version;
- generation parameters;
- raw response where appropriate;
- parsed response;
- token usage when available;
- latency;
- retries;
- validation errors;
- final acceptance/rejection.

Secrets and credentials must never be included in logs.

## ADR-011 — Provider health and fallback are first-class

**Status:** Accepted

Routing must account for provider health. Authentication failure, quota exhaustion, saturation and repeated transient errors can temporarily remove a provider/model from automatic selection. Fallback attempts and reasons are logged.

## ADR-012 — Persistent character roots + Character DNA

**Status:** Accepted

Recurring synthetic characters have immutable root references plus structured textual Character DNA. Shot prompts compile from these canonical identity assets rather than regenerating identity from prose each time.

## ADR-013 — Style Bible is a production anchor

**Status:** Accepted

Each production should have an approved canonical Style Bible frame/textual style description before bulk generation. Visual QC can compare shots against this anchor and retry style-drift failures.

## ADR-014 — Centralized consistency policy

**Status:** Accepted

Character/style/location/continuity reference selection belongs in a centralized policy/compiler layer. Individual generation stages should not independently improvise reference strategy.

## ADR-015 — Vertical drama is an explicit directing preset

**Status:** Accepted

9:16 microdrama uses dedicated story and composition rules: immediate hook, compact dialogue, frequent event/emotional change, escalating conflict, reversal/cliffhanger logic, mobile-readable subject scale and subtitle/UI safe areas.

## ADR-016 — Rich shot contract with optional micro-beats

**Status:** Accepted

Shots carry structured cinematography, narrative, timing and reference data. A shot may include temporal micro-beats describing how action evolves inside a generated clip.

## ADR-017 — Continuity groups may require sequential generation

**Status:** Accepted

Independent shots can generate in parallel. Connected shots may generate sequentially so the actual final frame of Shot N can anchor Shot N+1. The scheduler must support this speed/continuity tradeoff.

## ADR-018 — Quality is pass/warn/block, not one score

**Status:** Accepted

QC is multi-dimensional. Identity, style, continuity, media health, retention and other gates return `pass`, `warn` or `block` plus reasons and repair recommendations.

## ADR-019 — Targeted retry over whole-episode regeneration

**Status:** Accepted

Failed shots/assets are versioned and regenerated individually. Preserve rejected takes and reasons for telemetry. Segment-level retakes are a later optimization.

## ADR-020 — Generated assets must be persisted immediately

**Status:** Accepted

Provider URLs are not archival storage. Generated outputs are copied into Xerama-controlled persistent storage and recorded with content hash and lineage.

## ADR-021 — SQLite first behind repository interfaces

**Status:** Accepted for Trial 01

Trial 01 uses SQLite for metadata/state persistence. Domain code must use repository abstractions so PostgreSQL can replace SQLite later without redesigning story/production logic.

## ADR-022 — Local asset storage first, object storage later

**Status:** Accepted for Trial 01

Trial 01 stores assets locally in a structured persistent store. Storage access is abstracted so S3-compatible object storage can be introduced later.

## ADR-023 — Expensive generation uses persistent jobs

**Status:** Accepted

Image/video/audio generation is represented by persisted jobs with at least `queued`, `running`, `retrying`, `succeeded`, `failed` and `cancelled` states. Jobs record attempts, errors, provider/model, cost and resulting assets.

## ADR-024 — Optimize cost per accepted output

**Status:** Accepted

Raw provider price is insufficient. Xerama evaluates models/providers using cost per accepted image, accepted video second and accepted episode, incorporating retries and rejection rates.

## ADR-025 — FFmpeg/ffprobe is the deterministic finishing layer

**Status:** Accepted

After creative assets pass QC, FFmpeg/ffprobe handles deterministic assembly, trimming, transitions, subtitles, audio mixing, final encoding and media-health inspection.

## ADR-026 — Support native, TTS/lipsync and hybrid audio

**Status:** Accepted

Xerama defines three logical audio modes: `native`, `tts_lipsync` and `hybrid`. Exact scripted dialogue and persistent character voice identity can justify controlled TTS/lip-sync even when a video model supports native audio.

## ADR-027 — Research references do not create implementation dependency

**Status:** Accepted

Wind Comic and other public systems are architectural research references, not runtime dependencies. Before actual upstream source code is copied/adapted, record exact repository commit, source path, license and required notices.
