# Open-Source AI Drama Systems to Study

_Last researched: 2026-08-24_

## Goal

Before writing Xerama from scratch, inspect working public implementations and borrow architectural patterns where their licenses allow it. We should copy proven *ideas and patterns*, and reuse source code only when the repository license permits it and attribution/notice requirements are followed.

## 1. Wind Comic

Repository:
- https://github.com/ChrisChen667788/wind-comic

License: MIT at time of research.

Why it matters: this is currently one of the closest public analogues to Xerama. Its advertised pipeline is:

```text
idea
→ Writer
→ Director
→ Style Bible
→ Character Designer
→ Scene Designer
→ Storyboard
→ Video
→ TTS
→ Lip Sync
→ Editor
→ final MP4
```

Useful implementation ideas to inspect:

- provider-agnostic LLM configuration
- multiple specialist agents rather than one giant prompt
- reusable characters
- Style Bible Frame
- structured character DNA injected into shot prompts
- vision audit and automatic regeneration
- character resemblance scoring and retry
- pacing audit
- vertical-drama trope templates
- subtitle post-processing rather than asking video models to render text
- multiple video engines
- per-stage concurrency
- final timeline/editor

The project specifically documents a useful continuity tradeoff: higher video concurrency can weaken a previous-frame continuity chain, so sequential generation may be necessary inside a connected shot sequence.

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

- FastAPI backend
- React/TypeScript frontend
- MongoDB persistence
- Celery + Redis queues split by LLM/image/video/merge work
- OpenRouter LLM gateway
- character face lock
- look lock for hair/costume/accessories
- three canonical character views
- review gates before expensive generation
- `last_frame_url` chaining between connected shots
- parallelization across independent segments

This is especially relevant to Xerama's planned backend/task architecture.

## 3. StoryMind

Repository:
- https://github.com/LinHao-city/StoryMind

Useful concepts:

- storyboard-first generation
- structured shot scale/camera/lighting fields
- CharacterSheet descriptions injected verbatim into every relevant shot
- SceneConsistencyTracker for color/lighting anchors
- provider scoring/routing
- budget governance and pre-execution cost estimation
- FFmpeg/Remotion assembly
- approval points at creative decisions

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

- every shot exists as a still before video
- same character reference sheet passed into scene generation
- keyframe bridging with start/end images
- API-call manifests containing prompt/model/timing information
- generation is reproducible and auditable

## 5. DramaDirector

Repository:
- https://github.com/iLearn-Lab/DramaDirector

Paper:
- https://arxiv.org/abs/2606.24107

License: MIT at time of research.

This is important because it studies *short-drama-specific cinematography* rather than generic video generation.

Key ideas:

- structured storyboard schema
- shot scale
- camera angle
- camera motion
- character position
- action/expression
- duration
- dialogue/speaker/emotion
- retrieve real short-drama depth/pose patterns
- first-frame generation before video synthesis
- text-visual alignment reward

DramaBoard contains data derived from 35 live-action dramas, 2.8K episodes, and 81K shots according to the paper. Xerama should study its schema and evaluation design even if we do not reproduce its training pipeline initially.

## 6. MovieAgent

Repository:
- https://github.com/showlab/MovieAgent

Useful older reference for hierarchical agent planning and character assets. Its dataset convention includes script synopsis plus per-character photos and audio, which reinforces the principle that identity/voice assets should be first-class production objects rather than prompt text.

## 7. Awesome AI Short Drama

Repository:
- https://github.com/PAMPAS-Lab/awesome-ai-short-drama

This is a living index of short-drama-specific systems, research, benchmarks, agent skills, and production tools. Re-check it before major architecture decisions because the field is moving quickly.

Projects listed there include Wind Comic, OnlyShot, dramai, ViMax, MovieAgent, MM-StoryAgent, DramaDirector and others.

## Research conclusion

We should not invent Xerama's core workflow from nothing. Public systems independently converge on the same architecture:

```text
structured story
→ canonical assets
→ storyboard
→ first/reference frames
→ short video shots
→ reviewer/retry
→ audio/lipsync
→ deterministic editor
```

Xerama's opportunity is to combine the best patterns into a simpler production system optimized specifically for **serialized vertical microdrama**, free-first experimentation, automatic benchmarking, and later paid-model routing.

## Code reuse rule

Before copying source code from another repository:

1. verify its current LICENSE;
2. record repository URL + commit SHA;
3. preserve required copyright/license notices;
4. do not assume a GitHub repository is commercially reusable merely because it is public;
5. prefer adapting architecture/patterns when licensing is unclear.
