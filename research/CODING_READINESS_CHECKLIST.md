# Coding Readiness Checklist

_Last updated: 2026-08-24_

## Purpose

Research does not need to be perfect before coding. It needs to remove enough unknowns that Xerama V1 can be implemented as an experiment without major architectural rework.

## Story / product research

- [x] Define vertical microdrama episode grammar.
- [x] Define hooks, escalation, reversals, information gaps, cliffhangers.
- [x] Define multi-episode reveal ladder.
- [x] Define two-candidate + judge workflow.
- [x] Define canonical series state concept.
- [x] Define continuity validation categories.
- [x] Define story/production quality metrics.
- [ ] Build a small library of real microdrama episode breakdowns for prompt examples and benchmark cases.
- [ ] Finalize Trial 01 genre/premise constraints.

## Character research

- [x] Confirm reference-first character locking is a common production pattern.
- [x] Research real-actor/digital-likeness use in current AI microdramas.
- [x] Define original synthetic vs licensed likeness modes.
- [x] Add rights metadata requirement.
- [x] Define root portrait + character sheet approach.
- [ ] Test which free/trial image model best preserves one synthetic identity across 10 target stills.

## Storyboard/directing research

- [x] Confirm storyboard/first-frame-first architecture.
- [x] Define structured shot fields.
- [x] Research spatial consistency / geometry approaches.
- [x] Research previous-frame/keyframe chaining.
- [ ] Create Trial 01 shot grammar presets.

## Model/provider research

- [x] Select OpenRouter as initial LLM gateway.
- [x] Confirm free router and explicit free variants.
- [x] Confirm structured JSON output support.
- [x] Define pinned vs random free-model testing.
- [x] Map image/video/audio/lip-sync layers.
- [x] Decide provider adapters are mandatory.
- [ ] Snapshot exact free LLM candidates immediately before implementation.
- [ ] Identify at least one practical free/trial path for character still generation.
- [ ] Identify at least one practical free/trial path for image-to-video generation.

## Existing-system research

- [x] Identify complete open-source AI drama systems.
- [x] Identify reusable architectural patterns.
- [x] Identify short-drama-specific academic systems/benchmarks.
- [ ] Inspect selected repositories at source-code level before implementing equivalent modules.
- [ ] Record license + commit SHA for any source code we actually reuse.

## Infrastructure design

- [x] Python-first backend decision.
- [x] Structured JSON contracts drafted.
- [x] Canonical data model drafted.
- [x] Environment configuration drafted.
- [x] Generation telemetry requirement defined.
- [x] Human approval/review gates defined conceptually.
- [ ] Choose V1 persistence: SQLite/Postgres vs document database.
- [ ] Choose V1 async strategy: synchronous prototype vs queue from day one.
- [ ] Choose asset storage layout.

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

- concept generation quality
- schema success/failure
- judge decisions
- canon consistency
- character identity consistency
- accepted shots / generated shots
- retries per shot
- provider/model used
- generation latency
- actual cost
- human intervention
- final episode duration

## Coding start gate

We are ready to begin XER-001 implementation when these remaining items are resolved:

1. exact initial free LLM benchmark set;
2. V1 database/storage choice;
3. V1 async execution choice;
4. Trial 01 premise/genre;
5. initial image/video provider path for the media experiment.

Media providers do **not** need to be perfect before Story Engine coding starts. Provider adapters allow us to replace them later.

## Current assessment

**Research status: close to Story Engine coding readiness.**

The largest remaining uncertainty is not architecture. It is empirical provider/model quality. That should be solved by benchmarks and Trial 01 rather than more speculative design.
