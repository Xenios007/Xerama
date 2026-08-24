# Production Stack 2026

_Last researched: 2026-08-24_

## Core conclusion

The winning architecture is not one AI model. It is a routed production stack where each stage uses the model best suited to that job.

```text
LLM
→ Character/Environment Image Model
→ Storyboard/First Frames
→ Video Model
→ Voice
→ Lip Sync / Performance
→ Music + SFX
→ Deterministic Editor
→ Multimodal QC
```

## LLM / orchestration

### OpenRouter

Use first because it provides one OpenAI-compatible interface across many models, including free variants and structured-output-capable models.

Sources:
- https://openrouter.ai/docs/guides/routing/routers/free-router
- https://openrouter.ai/docs/guides/features/structured-outputs

Xerama requirement: logical model roles, pinned benchmark models, fallbacks, usage/cost telemetry.

## Character and environment images

The exact model can change; the required capability is more important:

- multiple image references
- identity preservation
- image editing
- controlled wardrobe
- multiple angles
- environment consistency

### Runway Gen-4 References

Official documentation says References can preserve a character across different lighting, locations, and treatments from a reference image and can combine multiple references.

Source:
- https://help.runwayml.com/hc/en-us/articles/40042718905875-Creating-with-Gen-4-Image-References

Runway's API model list currently includes multiple image models with reference inputs, including Gen-4 Image and other provider models exposed through its API.

Source:
- https://docs.dev.runwayml.com/guides/models/

## Video generation

Current production systems frequently route between multiple engines rather than committing to one.

### Runway API

Runway's current API exposes image-to-video and multiple model choices. Its API documentation lists current models and accepts prompt images/references depending on model.

Sources:
- https://docs.dev.runwayml.com/api/
- https://docs.dev.runwayml.com/assets/inputs/

### Google Veo

Google's Vertex AI documentation for Veo 3 documents vertical 9:16 output, 720/1080 resolutions, and short clip lengths. Later provider integrations expose additional keyframe/reference capabilities depending on the model/version.

Source:
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-0-generate-001

### Seedance / Kling / other engines

Public short-drama systems frequently integrate Seedance, Kling, Veo, MiniMax/Hailuo and others. Xerama should treat them as interchangeable adapters and benchmark them per shot category rather than declare one universal winner.

References:
- https://github.com/ChrisChen667788/wind-comic
- https://github.com/wushaojun321/ai-short-film
- https://github.com/LinHao-city/StoryMind

## Shot categories should route differently

Potential routing classes:

```text
DIALOGUE_CLOSEUP
TWO_SHOT
ACTION
ESTABLISHING
INSERT
REACTION
ROMANCE_CLOSEUP
CROWD
VFX_FANTASY
TRANSITION
```

A model that is excellent at a cinematic establishing shot may not be best at identity-sensitive dialogue.

## Video generation unit

Do not generate an entire episode in one request.

Production guidance converges on short individual clips, commonly several seconds each. Ogun Studios recommends splitting scenes into roughly 5–15 second chunks with one camera instruction and one action/dialogue unit per cut.

Source:
- https://ogunstudios.com/blog/how-to-make-ai-short-drama

## First-frame / storyboard-first strategy

Strong public implementations create still frames before video generation. This gives the production system a stable target for:

- identity
- pose
- framing
- wardrobe
- location
- lighting
- composition

Relevant references:
- https://github.com/0xadvait/ai-video-pipeline
- https://github.com/iLearn-Lab/DramaDirector

## Dialogue

Dialogue is a special production problem. Tight singles and over-the-shoulder shots reduce multi-character identity confusion and simplify lip sync/editing.

For dialogue scenes Xerama should prefer:

```text
speaker single
reaction single
speaker single
reaction
insert/cutaway
```

instead of forcing a video model to maintain two talking faces for long continuous takes.

## Voice

Voice should be stored as a character asset independent from the video provider.

Each character needs:

- voice provider
- voice ID
- language
- speaking style
- allowed usage/rights metadata
- pronunciation dictionary

This allows the same character to survive provider changes.

## Lip sync / performance transfer

Keep lip sync behind an adapter. Public AI drama systems already route among multiple providers, and Runway also documents Act-Two workflows for character performance/dialogue.

Sources:
- https://help.runwayml.com/hc/en-us/articles/41748090660499-Creating-Multi-Character-Dialogues-with-Act-Two
- https://github.com/ChrisChen667788/wind-comic

## Editing

The final assembly should be deterministic code, not generative AI.

Recommended V1:

- FFmpeg
- timeline JSON/EDL
- subtitle generation
- audio mixing
- loudness normalization
- transitions only when specified
- final 9:16 render

Why: once the assets are approved, deterministic editing is cheaper, repeatable, testable, and does not introduce visual drift.

## QC

Use multimodal models later for automated review, but retain programmatic checks:

- missing file
- wrong duration
- wrong aspect ratio
- black/corrupt frames
- audio clipping
- subtitle overflow
- duplicate shot
- continuity metadata mismatch

## Cost control architecture

Every provider call should eventually record:

```text
provider
model
operation
input assets
prompt hash
output asset
latency
credits/cost
retry number
accepted/rejected
rejection reason
```

This turns Trial 01 into useful production research rather than a collection of random generations.
