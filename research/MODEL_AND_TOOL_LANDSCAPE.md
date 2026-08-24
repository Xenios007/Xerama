# AI Microdrama Model & Tool Landscape

_Last researched: 2026-08-24_

## Principle

Xerama should never assume that one model will make the entire show. Existing workflows increasingly combine models and route work by capability. The model market changes too quickly to hard-code today's winner.

## Layer 1 — LLM / Story intelligence

Use LLMs for:

- concept generation
- season architecture
- episode beats
- scripts/dialogue
- critique/judging
- continuity checks
- prompt compilation
- metadata extraction

### Initial Xerama strategy

Use OpenRouter as the first gateway. Start with currently available free models and generate at least two independent candidates in Standard mode. Benchmark actual outputs before paying for premium models.

Do not permanently encode model names in business logic.

## Layer 2 — Image/reference generation

Purpose:

- casting/root portrait
- character turnaround/reference sheets
- expressions
- wardrobe states
- location/environment sheets
- props
- storyboard/keyframes
- shot reference frames

The important capability is not merely image beauty; it is controllability and reuse of identity/style references.

Potential providers/models should be benchmarked for:

- identity consistency
- multi-reference support
- editing/reference transformation
- pose control
- text rendering when needed
- API availability
- cost
- speed

## Layer 3 — Video generation

Frequently cited in current AI-drama workflows:

- ByteDance Seedance family
- Kling family
- Google Veo family
- other lower-cost/value models for B-roll or non-critical shots

Do not treat blog claims about a single "best" model as permanent. Benchmark by shot class.

### Google Veo capabilities verified from official documentation

Google's Vertex AI documentation lists native 9:16 support for Veo models. Veo 3.1 supports first/last-frame workflows, and preview/reference workflows support asset reference images. Veo 3 models support generated audio in applicable modes. API clip duration and reference capabilities vary by exact model/version.

This confirms why Xerama's adapter must expose capabilities rather than assume every video provider accepts the same inputs.

### Future routing dimensions

```text
shot_type
character_count
dialogue_required
native_audio_required
reference_images_required
first_last_frame_required
motion_complexity
camera_complexity
quality_tier
budget_tier
latency_target
```

The router can then select an eligible provider.

## Layer 4 — Voice

Voice system requirements:

- persistent voice ID per character
- multilingual support
- emotion/style control
- timing control
- API generation
- commercial usage clarity

Potential categories include dedicated TTS/voice platforms and native audio from video models.

## Layer 5 — Lip sync

Needed when video and dialogue are generated separately. Xerama should treat lip sync as optional per shot because native audiovisual generation may eliminate this stage for some models.

## Layer 6 — Music / SFX

Can initially use stock/licensed assets or generative services. We should not make music generation a blocker for V1.

## Layer 7 — Editing

For automated production, FFmpeg is the obvious baseline orchestration layer because it can:

- concatenate clips
- mix audio
- normalize/trim
- burn subtitles
- scale/crop
- encode 9:16 masters
- create platform variants

A human NLE can remain an escape hatch during trial runs.

## Layer 8 — Orchestration

Existing commercial/node-based workflows demonstrate that the key product is the pipeline connecting all these stages. Xerama should build its own orchestration and data layer while consuming external models through adapters.

## Provider capability contract

Future adapters should report capabilities, for example:

```json
{
  "provider": "example",
  "model": "example-video-model",
  "text_to_video": true,
  "image_to_video": true,
  "reference_images": true,
  "first_frame": true,
  "last_frame": false,
  "native_audio": false,
  "native_9_16": true,
  "max_duration_seconds": 10
}
```

The production planner should only request features the chosen adapter supports.

## Free-first testing policy

1. Story: free OpenRouter models first.
2. Images: use free credits/local/open models where practical.
3. Video: use trials/free credits/value tiers to prove interfaces.
4. Never optimize quality prematurely.
5. Record every generation's model, prompt, settings, duration, latency, cost/credits, pass/fail, and reason for rejection.
6. Upgrade to paid models only when benchmark data shows a bottleneck.

## Sources

- OpenRouter models/catalog: https://openrouter.ai/models
- Google Vertex AI Veo model documentation: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-0-generate-001
- Google Veo first/last frames: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/generate-videos-from-first-and-last-frames
- Google Veo reference images: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/use-reference-images-to-guide-video-generation
- https://ogunstudios.com/blog/how-ai-micro-dramas-are-produced
- https://www.minionarts.com/blogs/ai-microdrama-tool-stack-2026
- https://www.minionarts.com/blogs/how-ai-microdramas-are-made-node-based-pipeline
