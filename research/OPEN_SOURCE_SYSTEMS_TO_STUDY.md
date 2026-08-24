# Open-Source AI Drama Systems to Study

_Last researched: 2026-08-24_

## Goal

Before writing Xerama from scratch, inspect working public implementations and borrow architectural patterns where their licenses allow it. We should copy proven *ideas and patterns*, and reuse source code only when the repository license permits it and attribution/notice requirements are followed.

## 1. Wind Comic — primary implementation reference

Repository:
- https://github.com/ChrisChen667788/wind-comic

Dedicated source-level analysis:
- `research/WIND_COMIC_DEEP_DIVE.md`

License: MIT at time of research. Pin the exact commit before any code reuse and review bundled dependency licenses separately.

### Why it matters

Wind Comic is currently the closest public analogue to Xerama and has now been reviewed at source level rather than only through README claims. Its implemented/advertised system covers specialist agents, character/style locking, provider routing, generation jobs, quality gates, retakes/versioning, cost attribution, multi-episode memory, FFmpeg composition and vertical-drama-specific audits.

Its high-level production shape is:

```text
idea/source
→ Writer
→ Director
→ Style Bible
→ Character Designer
→ Scene Designer
→ Storyboard
→ Image/Video generation
→ Vision QC / retry
→ TTS/native audio
→ Lip Sync where needed
→ Editor
→ publish gate
→ final MP4
```

### Patterns Xerama should adopt early

- provider-agnostic LLM configuration;
- specialist agents/stages rather than one giant prompt;
- capability-bearing image/video provider adapters;
- provider health/circuit breaking and fallback;
- reusable root character references;
- structured Character DNA injected into shot prompts;
- centralized consistency/reference policy;
- Style Bible Frame;
- character resemblance scoring and automatic retry;
- style vision audit and automatic retry;
- vertical-drama hook/pacing/cliffhanger logic;
- conflict-curve analysis;
- dialogue coverage audit;
- mobile 9:16 composition rules;
- rich shot contracts and temporal micro-beats;
- storyboard/sketch layout before final render;
- previous-video-last-frame continuity;
- persistent series memory/recaps and anchor propagation;
- persistent generation jobs;
- content-addressed/persistent assets;
- SQLite-to-Postgres abstraction pattern;
- local-to-object-storage abstraction pattern;
- cost attribution by provider/stage/shot;
- take/retake/version lineage;
- targeted/segment retake concept;
- FFmpeg/ffprobe deterministic finishing;
- pass/warn/block quality/publish gates;
- native audio + TTS/lipsync hybrid strategy;
- stale/dirty dependency concepts for rerunning only affected stages.

### Continuity tradeoff

The project documents a useful scheduling tradeoff: higher video concurrency improves throughput but can weaken previous-frame continuity. Xerama should therefore parallelize independent shots while allowing sequential generation inside continuity groups.

### What not to copy into V1

Wind Comic also contains collaboration, billing, plan gating, rich timeline UI, team workspace and other product features. These prove production maturity but are not required for Xerama Trial 01. We should copy the production architecture first, not the entire product surface.

## 2. AI Short Film Production System

Repository:
- https://github.com/wushaojun321/ai-short-film

License: MIT at time of research.

Architecture:

```text
Screenplay
→ Episode Splitting
→ Character/Scene Assets
→ Human Review
→ Storyboard
→ Per-Shot Images
→ Chained Video Synthesis
→ Episode Merge
```

Techniques worth copying:

- FastAPI backend;
- React/TypeScript frontend;
- MongoDB persistence;
- Celery + Redis queues split by LLM/image/video/merge work;
- OpenRouter LLM gateway;
- character face lock;
- look lock for hair/costume/accessories;
- three canonical character views;
- review gates before expensive generation;
- `last_frame_url` chaining between connected shots;
- parallelization across independent segments.

This is especially relevant to Xerama's planned backend/task architecture.

## 3. StoryMind

Repository:
- https://github.com/LinHao-city/StoryMind

Useful concepts:

- storyboard-first generation;
- structured shot scale/camera/lighting fields;
- CharacterSheet descriptions injected verbatim into every relevant shot;
- SceneConsistencyTracker for color/lighting anchors;
- provider scoring/routing;
- budget governance and pre-execution cost estimation;
- FFmpeg/Remotion assembly;
- approval points at creative decisions.

## 4. AI Video Pipeline

Repository:
- https://github.com/0xadvait/ai-video-pipeline

Useful because it is deliberately reproducible rather than a large studio app.

Documented pattern:

```text
story
→ storyboard panels
→ one character bible
→ scene panels
→ video clips
→ FFmpeg final cut
```

Important ideas:

- every shot exists as a still before video;
- same character reference sheet passed into scene generation;
- keyframe bridging with start/end images;
- API-call manifests containing prompt/model/timing information;
- generation is reproducible and auditable.

## 5. DramaDirector

Repository:
- https://github.com/iLearn-Lab/DramaDirector

Paper:
- https://arxiv.org/abs/2606.24107

License: MIT at time of research.

This is important because it studies *short-drama-specific cinematography* rather than generic video generation.

Key ideas:

- structured storyboard schema;
- shot scale;
- camera angle;
- camera motion;
- character position;
- action/expression;
- duration;
- dialogue/speaker/emotion;
- retrieve real short-drama depth/pose patterns;
- first-frame generation before video synthesis;
- text-visual alignment reward.

DramaBoard contains data derived from 35 live-action dramas, 2.8K episodes and 81K shots according to the paper. Xerama should study its schema and evaluation design even if we do not reproduce its training pipeline initially.

## 6. MovieAgent

Repository:
- https://github.com/showlab/MovieAgent

Useful older reference for hierarchical agent planning and character assets. Its dataset convention includes script synopsis plus per-character photos and audio, which reinforces the principle that identity/voice assets should be first-class production objects rather than prompt text.

## 7. Awesome AI Short Drama

Repository:
- https://github.com/PAMPAS-Lab/awesome-ai-short-drama

This is a living index of short-drama-specific systems, research, benchmarks, agent skills and production tools. Re-check it before major architecture decisions because the field is moving quickly.

Projects listed there include Wind Comic, OnlyShot, dramai, ViMax, MovieAgent, MM-StoryAgent, DramaDirector and others.

## Research conclusion

We should not invent Xerama's core workflow from nothing. Public systems independently converge on the same architecture, and Wind Comic now gives us a particularly deep implementation reference:

```text
structured story
→ canonical state/assets
→ style/character locks
→ storyboard
→ first/reference frames
→ provider-routed short video shots
→ automated reviewer/retry
→ audio/lipsync
→ deterministic editor
→ final quality gate
```

Xerama's opportunity is to combine the best patterns into a simpler production system optimized specifically for **serialized vertical microdrama**, free-first experimentation, automatic benchmarking, structured canon and later paid-model routing.

## Code reuse rule

Before copying source code from another repository:

1. verify its current LICENSE;
2. record repository URL + exact commit SHA;
3. preserve required copyright/license notices;
4. review relevant dependency licenses;
5. do not assume a GitHub repository is commercially reusable merely because it is public;
6. prefer adapting architecture/patterns when licensing is unclear.
