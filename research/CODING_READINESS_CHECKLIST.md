# Coding Readiness Checklist

_Last updated: 2026-08-24_

## Purpose

Research does not need to be perfect before coding. It needs to remove enough unknowns that Xerama V1 can be implemented as an experiment without major architectural rework.

Wind Comic has now been inspected at source level and materially reduces uncertainty around provider abstraction, character/style consistency, jobs/assets, QC, continuity and finishing architecture. See `research/WIND_COMIC_DEEP_DIVE.md`.

## Story / product research

- [x] Define vertical microdrama episode grammar.
- [x] Define hooks, escalation, reversals, information gaps, cliffhangers.
- [x] Define multi-episode reveal ladder.
- [x] Define two-candidate + judge workflow.
- [x] Define canonical series state concept.
- [x] Define continuity validation categories.
- [x] Define story/production quality metrics.
- [x] Validate deterministic/semi-deterministic hook, pacing and cliffhanger audit patterns from a working system.
- [ ] Build a small library of real microdrama episode breakdowns for prompt examples and benchmark cases.
- [ ] Finalize Trial 01 genre/premise constraints.

## Character research

- [x] Confirm reference-first character locking is a common production pattern.
- [x] Research real-actor/digital-likeness use in current AI microdramas.
- [x] Define original synthetic vs licensed likeness modes.
- [x] Add rights metadata requirement.
- [x] Define root portrait + character sheet approach.
- [x] Validate Character DNA + centralized consistency-policy pattern from Wind Comic.
- [x] Validate vision-based resemblance retry pattern.
- [x] Validate Style Bible + style vision audit pattern.
- [ ] Test which free/trial image model best preserves one synthetic identity across 10 target stills.

## Storyboard/directing research

- [x] Confirm storyboard/first-frame-first architecture.
- [x] Define structured shot fields.
- [x] Research spatial consistency / geometry approaches.
- [x] Research previous-frame/keyframe chaining.
- [x] Validate real-last-frame continuity chaining from Wind Comic.
- [x] Validate dialogue-coverage audit concept.
- [x] Validate temporal micro-beats inside a generated shot.
- [x] Validate vertical/mobile composition rules beyond aspect ratio.
- [ ] Create Trial 01 shot grammar presets.

## Model/provider research

- [x] Select OpenRouter as initial LLM gateway.
- [x] Confirm free router and explicit free variants.
- [x] Confirm structured JSON output support.
- [x] Define pinned vs random free-model testing.
- [x] Map image/video/audio/lip-sync layers.
- [x] Decide provider adapters are mandatory.
- [x] Define capability-bearing image/video provider contracts.
- [x] Define provider health/circuit-break/fallback requirement.
- [x] Define `native | tts_lipsync | hybrid` audio modes.
- [ ] Snapshot exact free LLM candidates immediately before implementation.
- [ ] Identify at least one practical free/trial path for character still generation.
- [ ] Identify at least one practical free/trial path for image-to-video generation.

## Existing-system research

- [x] Identify complete open-source AI drama systems.
- [x] Identify reusable architectural patterns.
- [x] Identify short-drama-specific academic systems/benchmarks.
- [x] Inspect Wind Comic at source-code level before implementing equivalent modules.
- [ ] Inspect additional selected repositories at source-code level where they cover gaps not already answered by Wind Comic.
- [ ] Record license + exact commit SHA for any source code we actually reuse.

## Infrastructure design

- [x] Python-first backend decision.
- [x] Structured JSON contracts drafted.
- [x] Canonical data model drafted.
- [x] Environment configuration drafted.
- [x] Generation telemetry requirement defined.
- [x] Human approval/review gates defined conceptually.
- [x] Choose V1 persistence: **SQLite behind repository interfaces**.
- [x] Choose V1 asset storage: **local persistent storage first, S3-compatible adapter later**.
- [x] Decide generation jobs must be persistent and restart-safe.
- [x] Define minimum job states: queued/running/retrying/succeeded/failed/cancelled.
- [x] Define take/version lineage and targeted shot retry.
- [x] Define FFmpeg/ffprobe as deterministic finishing/media-health layer.
- [ ] Choose concrete Python queue implementation for Trial 01 (simple DB-backed worker vs Redis/Celery/RQ/etc.).

## Trial 01 target

The first experiment should be deliberately small:

```text
1 series
3 episodes
60–90 sec target each
2–3 principal characters
2 recurring locations
~8–15 shots per episode
original synthetic cast
free LLMs first
free/trial media where practical
```

The purpose is not to publish a masterpiece. The purpose is to expose the pipeline's real failure points.

## Trial 01 must measure

- concept generation quality;
- schema success/failure;
- judge decisions;
- hook/pacing/cliffhanger audit results;
- canon consistency;
- character identity consistency;
- Style Bible consistency;
- accepted shots / generated shots;
- retries per shot;
- provider/model used;
- provider fallback reason;
- generation latency;
- actual cost;
- cost per accepted image/video second/episode;
- human intervention;
- final episode duration.

## Coding start gate

Architecture is now sufficiently researched to begin XER-001. Remaining items are implementation-time selections or empirical experiments, not blockers to creating the core system.

Resolve in parallel with coding:

1. exact initial free LLM benchmark set;
2. concrete lightweight worker/queue implementation;
3. Trial 01 premise/genre;
4. initial free/trial image provider;
5. initial free/trial video provider.

Media providers do **not** need to be perfect before Story Engine coding starts. Provider adapters allow us to replace them later.

## Current assessment

**Research status: READY FOR CORE CODING.**

Wind Comic's running implementation validates enough of the production architecture that continued speculative architecture research now has diminishing returns. The largest remaining uncertainty is empirical provider/model quality. That should be solved by benchmarks and Trial 01 while the provider-independent core is implemented.
