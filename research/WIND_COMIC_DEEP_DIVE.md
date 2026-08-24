# Wind Comic Source-Level Deep Dive

_Last reviewed: 2026-08-24_

Source: https://github.com/ChrisChen667788/wind-comic

## Why this project matters to Xerama

Wind Comic is the strongest open-source reference found so far for Xerama because it is not merely a prompt collection or proof of concept. Its repository implements an end-to-end AI comic/short-drama production system with specialist agents, character/style consistency, provider routing, persistent jobs/assets, quality gates, editing, cost tracking, vertical-drama logic, and multi-episode continuity.

The important conclusion is not that Xerama should become a fork. The conclusion is that many architecture choices we had independently proposed have already been exercised in a running codebase. Xerama should reuse the proven patterns, preserve clean-room capability contracts where practical, and focus its experiments on English/global microdrama storytelling, model economics, character quality, serialized canon, and accepted-output cost.

## Source snapshot

Review performed against the Wind Comic repository state available on 2026-08-24. The project README describes a Next.js/TypeScript application with thousands of tests and a mature multi-stage production workflow. Before copying any implementation code, Xerama must pin the exact upstream commit and record the applicable MIT notice plus dependency licenses.

## 1. Overall production architecture

The system validates a specialist pipeline rather than a single monolithic generation call:

```text
Idea / source material
  -> Writer
  -> Director
  -> Style Bible
  -> Character design
  -> Scene design
  -> Storyboard / shot planning
  -> Image generation
  -> Vision QC + targeted retry
  -> Video generation / provider routing
  -> Audio / TTS / lip sync where required
  -> Editor / FFmpeg composition
  -> Quality / publish gates
  -> Final video
```

Wind Comic exposes agent-role contracts and an orchestrator. Xerama should use the same principle: specialist stages exchange typed production artifacts and every expensive generation step remains replaceable.

## 2. Provider abstraction is a core pattern to adopt

Wind Comic treats providers as capability-bearing adapters rather than hard-coded vendors.

Image providers expose properties such as reference-image support, maximum reference count, priority and generation behavior. Video providers advertise capabilities such as text-to-video, image-to-video, first/last-frame control, subject reference, native audio and duration limits.

Xerama should therefore implement a provider registry around capability contracts:

```text
requested shot capability
  -> eligible providers
  -> health filter
  -> price/quality policy
  -> preferred provider
  -> fallback chain
  -> result + telemetry
```

Provider health should include temporary circuit breaking for authentication, quota, saturation and repeated transient failures. A broken provider should not consume every job retry.

## 3. Character identity: reference image is not enough

Wind Comic's strongest reusable concept is a layered character identity system.

### Character DNA

The implementation derives a compact visual signature from a character reference, including stable traits such as eyes, jaw, nose, mouth, hairstyle, hair color, skin tone and signature outfit. This textual DNA can then be injected into shot prompts alongside visual references.

### Central consistency policy

Reference choice and strength are centralized. The shot generator should not independently decide how to represent a character. A consistency policy selects the canonical reference(s), character DNA and style references appropriate for the shot.

### Vision-based identity retry

Generated shots are checked for character resemblance. Low-scoring shots can be retried with stronger reference conditioning. Multi-character scenes should score each important character separately; a correct lead must not hide a failed supporting actor.

### Xerama target pattern

```text
Synthetic cast member
  -> permanent root reference
  -> multi-view character sheet
  -> Character DNA
  -> voice identity
  -> wardrobe/state variants
  -> LOCK
  -> shot generation
  -> identity QC
  -> strengthen/retry on failure
```

This should be part of Xerama V1, not a later optimization.

## 4. Style Bible before bulk generation

Wind Comic creates a canonical Style Bible frame before downstream image generation. It represents palette, lighting, color temperature, texture and general visual identity. Generated shots can then be compared against this anchor.

Xerama should generate and approve:

- a Style Bible image/frame;
- textual style DNA;
- palette and lighting descriptors;
- negative constraints;
- aspect-ratio/composition preset.

A vision audit should detect style drift and regenerate only failed assets.

## 5. Vertical microdrama is a distinct directing mode

Wind Comic contains explicit short/vertical-drama rules instead of asking a generic writer to make a short story.

Useful rules for Xerama include:

- hook immediately, especially in the opening seconds;
- each shot must create an event, revelation or emotional change;
- dialogue should be compact;
- conflict must escalate rather than remain flat;
- reversals should occur frequently enough for the format;
- end on a strong unresolved question, threat, reveal or reversal;
- compose specifically for 9:16 mobile viewing.

This supports a Xerama `VERTICAL_DRAMA` story/directing preset.

## 6. Deterministic retention audits

Wind Comic does not rely only on an LLM saying a script is good. It implements hook and pacing audits.

Xerama should maintain measurable checks for:

- first-3-second hook;
- conflict density;
- reversal count/density;
- conflict-curve shape;
- dead/flat sections;
- climax placement;
- ending cliffhanger strength;
- dialogue coverage;
- runtime budget.

A useful conflict-curve classification is:

```text
ESCALATING    preferred
FLAT          warn/fail
FRONT-LOADED  warn
NO CLIMAX     warn/fail
```

These deterministic or semi-deterministic metrics can complement an LLM story judge.

## 7. Dialogue coverage needs cinematic shot planning

A common AI-video failure is putting an entire conversation into one wide two-shot. Wind Comic audits dialogue coverage and expects reaction/reverse coverage.

Xerama's Director should consider patterns such as:

```text
A close-up
B reaction
A close-up
B close-up
insert/cutaway
reaction
```

The exact sequence should remain story-dependent, but multi-speaker dialogue should trigger a coverage check before expensive video generation.

## 8. 9:16 composition requires more than changing aspect ratio

Useful vertical composition rules include:

- center or deliberately stack important subjects;
- preserve headroom;
- avoid overly wide horizontal staging;
- use depth for multiple actors;
- keep subtitle/UI safe areas clear;
- favor readable close/medium shots on phone screens.

Xerama should compile these rules into shot prompts automatically when the target format is vertical.

## 9. Rich shot contracts and micro-beats

Wind Comic's shot representation includes more than prompt + duration. Relevant dimensions include camera size, lens, angle, movement, lighting, composition, sound, emotion, edit intent, narrative function and duration.

A particularly useful pattern is splitting a single generated clip into temporal micro-beats:

```text
8-second shot
0-2s: character turns
2-5s: sees antagonist; slow push-in
5-8s: expression changes; dialogue line
```

Xerama should support optional `micro_beats[]` in the canonical shot contract because current video models respond better when motion progression is explicit.

## 10. Storyboard layout before final image generation

Wind Comic can create rough storyboard/sketch references before expensive rendering. This separates composition decisions from visual polish.

Xerama should consider:

```text
shot intent
 -> rough layout / blocking
 -> approve geometry
 -> final keyframe
 -> video
```

This is particularly valuable for multi-character shots where left/right placement and eyelines matter.

## 11. Spatial/stage blocking is a future-proof extension

Wind Comic contains deterministic stage/blocking concepts where actors and cameras can be represented spatially. This enables checks such as left/right position, occlusion, camera framing and whether a subject is actually in frame.

Xerama V1 does not need a full virtual stage engine, but its shot schema should avoid designs that make later spatial coordinates impossible.

## 12. Clip-to-clip continuity using the real final frame

An important practical technique is extracting the actual last frame of generated Shot N and using it as a reference for Shot N+1. The generated final frame captures the real pose, lighting and expression better than the original storyboard.

Xerama should distinguish:

```text
independent shots -> parallel generation
continuous shots  -> sequential generation
                     -> extract final frame
                     -> use as next-shot reference
```

This creates an explicit quality/speed tradeoff: high concurrency is faster, while sequential generation can improve continuity.

## 13. Multi-episode memory and canon

Wind Comic added bounded previous-episode recap/context injection to reduce repetition and contradiction. It also propagates series anchors such as character/style assets.

Xerama should go beyond recap text and maintain structured canon:

- character facts and current state;
- relationships;
- secrets known by each character;
- injuries/deaths;
- wardrobe/location state;
- unresolved hooks;
- objects/props;
- episode outcomes;
- prior promises/foreshadowing.

A compact recap remains useful as LLM context, but canonical structured state should be the source of truth.

## 14. Quality should be a closed loop

Wind Comic validates a production loop of:

```text
GENERATE
 -> MEASURE
 -> DIAGNOSE
 -> RETRY ONLY FAILURE
 -> MEASURE AGAIN
 -> STORE TELEMETRY
```

Useful QC dimensions include:

- character resemblance;
- visual/style consistency;
- continuity;
- lighting;
- shot validity;
- pacing/hook quality;
- lip-sync readiness;
- media health.

Xerama should implement `pass / warn / block` gates rather than a single opaque quality score.

## 15. Targeted retakes and versioning

Wind Comic has patterns for shot takes, retakes, versions and even segment-level regeneration. This matters because regenerating a complete shot or episode is often unnecessarily expensive.

Xerama should version every generated asset and preserve lineage:

```text
shot-007
  take-001 rejected: face drift
  take-002 rejected: hand artifact
  take-003 accepted
```

Later, segment retakes can regenerate only the defective temporal region and splice it into the accepted clip.

## 16. Persistent assets are mandatory

Provider/CDN URLs can expire. Wind Comic persists generated assets and uses content-addressed/hash-oriented asset handling.

Trial 01 should therefore download every accepted or diagnostically useful output into Xerama-controlled storage immediately.

Recommended initial design:

```text
local asset store
  /project
    /characters
    /style
    /storyboards
    /images
    /video
    /audio
    /final
```

Store hashes, provider, model, prompt version, generation parameters, source references and acceptance status in the database. Add S3-compatible storage later behind an adapter.

## 17. SQLite first, PostgreSQL later

Wind Comic demonstrates a pragmatic local-first database strategy with an abstraction that permits PostgreSQL migration.

For Xerama Trial 01:

- SQLite is sufficient;
- all persistence should go through repositories/interfaces;
- avoid SQLite-specific assumptions in domain code;
- prepare for PostgreSQL only when concurrency/deployment requires it.

## 18. Persistent generation jobs

Generation should not be represented only by an in-memory HTTP request. Wind Comic uses persisted job concepts with states and progress/events.

Xerama should model at least:

```text
queued
running
retrying
succeeded
failed
cancelled
```

A job should record stage, provider/model, attempt number, timestamps, error class, cost and resulting asset IDs.

## 19. Cost attribution is part of the architecture

Wind Comic tracks costs around providers/stages/assets. Xerama's free-first strategy requires even stricter telemetry.

For every generation, record:

- provider;
- model;
- stage;
- shot/episode/project;
- input/output usage where available;
- monetary cost;
- latency;
- retry count;
- accepted/rejected;
- rejection reason.

The metric that matters is not raw API price. It is **cost per accepted asset/second/episode**.

## 20. FFmpeg remains the deterministic finishing layer

Wind Comic reinforces our plan to use FFmpeg/ffprobe for deterministic composition after creative assets are approved.

Xerama's editor should eventually handle:

- clip concatenation;
- trims;
- transitions;
- subtitle burn-in;
- audio mixing;
- loudness normalization;
- music/SFX;
- resolution/aspect validation;
- final encode;
- ffprobe media-health checks.

Creative generation should not be responsible for deterministic assembly tasks.

## 21. Native audio, TTS and lip sync should coexist

Modern video models can generate native audio, but exact dialogue and stable recurring voices remain concerns. Wind Comic supports multiple audio/lipsync paths.

Xerama should define:

```text
AUDIO_MODE = native | tts_lipsync | hybrid
```

`native` is useful when natural scene sound and speech are acceptable. `tts_lipsync` is preferable when exact dialogue and persistent voice identity matter. `hybrid` can preserve native ambience while replacing/overlaying controlled dialogue.

## 22. LLM gateway design validates OpenRouter/free-first testing

Wind Comic uses OpenAI-compatible LLM interfaces and documents BYO provider configuration. This reinforces the Xerama decision that Writer/Director/Judge roles should not depend on one LLM vendor.

Xerama should use role-based routing:

```text
story candidate -> cheap/free model
story judge     -> independent model
repair          -> best available model justified by failure
```

Promotion to paid models should be based on measured accepted-output improvement.

## 23. Prompt compilation should be centralized

Wind Comic contains prompt compilation/asset-reference concepts rather than assembling every prompt ad hoc.

Xerama should compile prompts from structured inputs:

```text
story intent
+ shot contract
+ character DNA/references
+ style bible
+ location/prop state
+ continuity anchor
+ provider capability rules
+ negative constraints
= provider-ready prompt/request
```

This is essential for reproducibility and later model swapping.

## 24. Staleness/dirty dependency tracking

The upstream project contains multiple concepts around stale assets and rerunning only affected stages. This is highly relevant to a production DAG.

Example:

```text
change dialogue only
 -> invalidate TTS/lipsync/subtitles/final edit
 -> do NOT invalidate character sheet

change character face
 -> invalidate dependent storyboards/images/videos
```

Xerama should eventually model asset dependencies and dirty propagation. Trial 01 can begin with coarse stage invalidation.

## 25. Human-in-the-loop remains valuable

Automation should not mean blind generation. Useful human approval points are:

1. premise/episode outline;
2. cast/root references;
3. Style Bible;
4. script/shot list;
5. storyboard/keyframes;
6. failed QC exceptions;
7. final publish gate.

The goal is to minimize expensive human review, not remove it before automated QC is trustworthy.

## 26. What Xerama should adopt now

High-priority Trial 01 patterns:

- specialist stage contracts;
- provider adapters + capability registry;
- provider health/fallback;
- persistent character root references;
- Character DNA;
- Style Bible;
- vertical-drama prompt/directing preset;
- structured shot contract + micro-beats;
- hook/pacing/cliffhanger audits;
- targeted shot regeneration;
- persistent assets;
- persistent jobs;
- SQLite repositories;
- generation/cost telemetry;
- FFmpeg deterministic assembly;
- structured series canon;
- pass/warn/block QC.

## 27. What can wait

Defer until the basic pilot works:

- full collaborative editing UI;
- team RBAC/invites;
- billing/plan gates;
- advanced timeline UX;
- complete spatial stage simulator;
- segment-level retakes;
- PostgreSQL deployment;
- S3/object-store deployment;
- elaborate preset galleries.

## 28. What Xerama should improve beyond Wind Comic

Xerama's differentiation should be system quality rather than UI feature count:

- English/global-first microdrama grammar;
- stronger structured canon instead of recap-only memory;
- explicit secrets/knowledge-state tracking;
- cost-per-accepted-output optimization;
- benchmark-driven provider promotion;
- free-first LLM/model routing;
- automated failure taxonomy;
- clean capability contracts independent of vendor names;
- reusable original synthetic cast library;
- stronger licensing/consent provenance for every identity asset.

## 29. Clean-room / licensing rule

Wind Comic is a research reference. Architectural ideas, interfaces and observed production patterns can inform Xerama. If actual source code is copied or adapted, first record:

- exact upstream commit;
- source file/path;
- license;
- required copyright notice;
- dependency implications;
- Xerama file containing the adaptation.

Do not blindly copy bundled provider code or dependency assumptions.

## 30. Revised Xerama reference architecture

```text
SOURCE / IDEA
    |
    v
STORY ENGINE
candidate writers -> judge -> retention audit
    |
    v
SERIES CANON + EPISODE STATE
    |
    v
DIRECTOR
shots + micro-beats + dialogue coverage + vertical composition
    |
    +--> STYLE BIBLE
    +--> CHARACTER ROOTS / DNA / VOICES
    +--> LOCATIONS / PROPS
    |
    v
STORYBOARD / KEYFRAME PLAN
    |
    v
PROMPT COMPILER
    |
    v
PROVIDER ROUTER
capabilities + health + cost/quality policy
    |
    v
IMAGE / VIDEO / AUDIO GENERATION
    |
    v
QC GATES
identity + style + continuity + media + retention
    |
    +--> targeted retry / alternate provider
    |
    v
FFMPEG EDITOR
    |
    v
FINAL QC / PUBLISH GATE
    |
    v
EPISODE + TELEMETRY + CANON UPDATE
```

## Bottom line

Wind Comic materially reduces Xerama's architectural uncertainty. We no longer need to invent the basic production shape from scratch. The sensible approach is to implement the smallest subset of these proven patterns, run Trial 01 with free/trial providers, measure failure and accepted-output cost, then promote only the components that demonstrably improve production quality.