# Xerama Architecture

## 1. Purpose

Xerama is designed as a provider-independent AI microdrama production platform. Story intelligence, canonical series state, directing, media generation, and quality control are separate layers so individual AI providers can be replaced without redesigning the application.

The architecture is informed by source-level study of working open-source systems, especially Wind Comic. We adopt proven production patterns without making Xerama dependent on Wind Comic or any single upstream implementation.

## 2. High-Level Architecture

```text
User / Studio
    ↓
Project Service
    ↓
Showrunner / Story Engine
    ├── Candidate Generator A
    ├── Candidate Generator B
    ├── Judge / Merge
    └── Hook / Pacing / Cliffhanger Audit
    ↓
Canonical Series State
    ├── Series Bible
    ├── Character State
    ├── Relationships
    ├── Knowledge / Secrets
    ├── Timeline
    ├── World State
    └── Unresolved Hooks / Payoffs
    ↓
Episode Engine
    ├── Beat Planner
    ├── Script Writer
    ├── Retention Critic
    └── Continuity Validator
    ↓
Director Engine
    ├── Scene Planner
    ├── Shot Planner
    ├── Dialogue Coverage
    ├── Vertical Composition
    ├── Micro-beat Planner
    └── Prompt Compiler
    ↓
Production Anchors
    ├── Style Bible
    ├── Character Root References
    ├── Character DNA
    ├── Voice Identity
    ├── Location References
    └── Prop References
    ↓
Provider Router
    ├── Capability Registry
    ├── Provider Health
    ├── Cost / Quality Policy
    └── Fallback Chain
    ↓
Media Engine
    ├── Image Provider
    ├── Video Provider
    ├── Voice / TTS Provider
    ├── Lip-sync Provider
    └── Native Audio Path
    ↓
QC Gates
    ├── Identity
    ├── Style
    ├── Continuity
    ├── Media Health
    └── Pass / Warn / Block
    ↓
Targeted Retry / Alternate Provider
    ↓
Deterministic FFmpeg Editor
    ↓
Final QC / Publish Gate
    ↓
Final Episode + Telemetry + Canon Update
```

## 3. Architectural Principles

### Canonical state over prompt memory
The database is the source of truth. Models receive only the state needed for their task. Model output does not become canon until validated and committed.

### Provider independence
Application services request capabilities such as `concept_generator`, `episode_writer`, `image_reference_generation`, `video_i2v`, `native_audio_video`, or `continuity_checker`; they should not depend directly on a specific model identifier.

### Capability-bearing provider adapters
Providers declare what they can actually do: reference images, maximum references, I2V/T2V, first/last-frame control, subject reference, native audio, duration limits, etc. Routing chooses among eligible healthy providers.

### Structured contracts
Important AI stages return validated structured data instead of unconstrained prose. This enables scoring, retries, comparison, persistence, and downstream automation.

### Generate before spending
Story, continuity, retention, composition, and production-feasibility checks happen before expensive image or video generation.

### Persistent production anchors
Characters, style, locations and important props have reusable root references. A shot should compile from canonical anchors rather than reconstructing identity from scratch.

### Closed-loop quality
Generation is followed by measurement, diagnosis and targeted retry. Regenerate the failed shot/asset/segment rather than the entire episode whenever possible.

### Deterministic finishing
Once creative assets are accepted, deterministic tools such as FFmpeg handle assembly, trims, subtitles, transitions, audio mixing and final encoding.

### Human override
Every major AI decision should eventually support approval, rejection, editing, regeneration and locking.

## 4. Initial Multi-Model Flow

Standard mode begins with two independent candidates.

```text
Input
  ├── Model A → Candidate A
  └── Model B → Candidate B
                  ↓
                Judge
                  ↓
             A / B / Merge
                  ↓
        Retention / Feasibility Audit
                  ↓
              Approved
```

The judge evaluates hook strength, emotional intensity, originality, serial potential, reversals, cliffhanger potential, character potential and production feasibility. Deterministic/semi-deterministic audits should complement the LLM judge rather than relying on one opaque score.

## 5. Model Gateway

The first LLM gateway is OpenRouter. Model configuration is externalized so free and paid models can be benchmarked and replaced without modifying story logic.

Planned logical roles:

- `concept_generator_a`
- `concept_generator_b`
- `story_architect`
- `judge`
- `episode_writer`
- `continuity_checker`
- `retention_critic`
- `shot_planner`
- `showrunner`

Paid models are promoted only when measured accepted-output quality justifies the cost.

## 6. Provider Registry

Media providers implement Xerama contracts and advertise capabilities. Routing should consider:

- requested capability;
- provider/model availability;
- provider health/circuit state;
- reference requirements;
- target duration/resolution/aspect;
- quality history;
- latency;
- estimated cost;
- historical accepted-output rate.

The primary optimization metric is **cost per accepted output**, not raw API price.

## 7. Series State

The canonical series state should eventually track:

- series metadata and creative constraints;
- characters and stable visual identities;
- character goals and emotional states;
- relationships;
- character knowledge;
- audience knowledge;
- secrets and reveal status;
- locations;
- wardrobe;
- props;
- injuries and physical state;
- timeline and chronology;
- episode events;
- unresolved questions;
- promises/payoffs;
- prior hooks and their resolution status.

Compact previous-episode recaps can be generated for model context, but recap text is not the source of truth.

## 8. Character and Style Anchors

Every recurring synthetic performer should have a permanent root reference and derived Character DNA. The initial identity package should support:

- root portrait/reference;
- multi-view character sheet;
- textual Character DNA;
- canonical voice;
- wardrobe/state variants;
- consent/provenance metadata.

Every production should also have an approved Style Bible frame and textual style description. Identity/style references are injected by centralized consistency policy, not improvised independently by each stage.

## 9. Shot Contract

A canonical shot should be able to represent:

- shot ID and narrative function;
- characters present;
- dialogue;
- duration;
- camera size/angle/lens/movement;
- composition and vertical safe-area guidance;
- lighting;
- emotion/beat;
- action;
- optional temporal `micro_beats[]`;
- sound/audio mode;
- character/style/location/prop references;
- continuity relationship to adjacent shots;
- provider requirements;
- acceptance/QC state.

Continuous shots may be generated sequentially so the actual last frame of Shot N can anchor Shot N+1. Independent shots may be generated concurrently.

## 10. Quality Gates

Quality is multi-dimensional. Planned gates include:

- character resemblance;
- style consistency;
- continuity;
- composition;
- media validity;
- hook/pacing/cliffhanger quality;
- dialogue coverage;
- lip-sync/audio validity;
- runtime budget.

Each gate can return `pass`, `warn`, or `block` plus reasons and recommended repair action.

## 11. Jobs, Assets and Versioning

All expensive generation should use persistent jobs rather than only in-memory request state.

Minimum states:

```text
queued -> running -> succeeded
                 -> retrying -> running
                 -> failed
                 -> cancelled
```

Generated assets are immediately persisted because provider URLs can expire. Every asset records lineage including provider/model, prompt version, references, hash, cost, latency, take/version and acceptance state.

Initial persistence strategy:

- SQLite through repository interfaces;
- local content-addressed/file storage;
- PostgreSQL and S3-compatible storage later behind adapters.

## 12. Audio Modes

Xerama supports three logical strategies:

- `native` — video model supplies speech/ambience;
- `tts_lipsync` — exact scripted voice is synthesized and lip-synced;
- `hybrid` — native ambience/effects combined with controlled dialogue.

Exact dialogue and persistent recurring voice identity may favor TTS/lip-sync even when native audio is available.

## 13. Planned Execution Modes

### Fast
One generation, minimal review.

### Standard
Two independent candidates plus judge and core deterministic audits. This is the initial default.

### Quality
Three or more candidates, judge, merge/rewrite, critic and additional validation/QC.

## 14. Trial 01 Scope

Trial 01 should prove the complete production skeleton with the cheapest practical providers rather than build a full studio UI.

Priority implementation:

1. typed project/series/episode/shot contracts;
2. SQLite repositories;
3. local asset storage;
4. OpenRouter LLM adapter;
5. provider registry and health/fallback;
6. story candidate + judge pipeline;
7. canonical series state;
8. vertical-drama retention audits;
9. character root/DNA and Style Bible records;
10. storyboard/keyframe generation path;
11. one image and one video provider adapter;
12. persistent generation jobs;
13. QC + targeted retakes;
14. FFmpeg assembly;
15. telemetry and cost-per-accepted-output report.

Advanced collaboration, billing, sophisticated timelines, full spatial blocking, PostgreSQL/S3 deployment and segment-level retakes can wait until the pilot works.

## 15. Research provenance

The source-level Wind Comic analysis that informed these additions is documented in `research/WIND_COMIC_DEEP_DIVE.md`. Wind Comic remains an external research reference; Xerama should record exact upstream commit/license information before reusing actual source code.