# Production Stack 2026

_Last researched: 2026-08-24_

## Core conclusion

The winning architecture is not one AI model. It is a routed production stack where each stage uses the model best suited to that job. Source-level study of Wind Comic provides a working implementation reference for this pattern.

```text
LLM / Story
→ Canon / Retention Audits
→ Style Bible + Character DNA
→ Character/Environment Image Model
→ Storyboard/First Frames
→ Provider Router
→ Video Model
→ Native Audio OR Voice/TTS + Lip Sync
→ Music + SFX
→ Deterministic Editor
→ Multimodal + Programmatic QC
```

## LLM / orchestration

### OpenRouter

Use first because it provides one OpenAI-compatible interface across many models, including free variants and structured-output-capable models.

Sources:
- https://openrouter.ai/docs/guides/routing/routers/free-router
- https://openrouter.ai/docs/guides/features/structured-outputs

Xerama requirement: logical model roles, pinned benchmark models, fallbacks, provider health and usage/cost telemetry.

Wind Comic independently validates the value of OpenAI-compatible BYO LLM routing and model fallbacks.

## Character and environment images

The exact model can change; the required capability is more important:

- multiple image references;
- identity preservation;
- image editing;
- controlled wardrobe;
- multiple angles;
- environment consistency.

### Runway Gen-4 References

Official documentation says References can preserve a character across different lighting, locations and treatments from a reference image and can combine multiple references.

Source:
- https://help.runwayml.com/hc/en-us/articles/40042718905875-Creating-with-Gen-4-Image-References

Runway's API model list currently includes multiple image models with reference inputs.

Source:
- https://docs.dev.runwayml.com/guides/models/

### Provider contract

Following the Wind Comic pattern, Xerama image adapters should expose capability metadata such as:

```text
supports_reference_images
max_reference_images
supports_edit
supports_mask
supported_aspects
priority
estimated_cost
```

The router should reject an incompatible provider before spending a generation request.

## Style Bible + Character DNA

Before bulk generation, Xerama should create:

- approved Style Bible frame;
- textual style DNA;
- root character references;
- multi-view character packs;
- structured Character DNA;
- canonical voice profiles.

These become persistent production anchors reused across shots and episodes.

## Video generation

Current production systems frequently route between multiple engines rather than committing to one.

### Runway API

Runway's current API exposes image-to-video and multiple model choices. Its API documentation lists current models and accepts prompt images/references depending on model.

Sources:
- https://docs.dev.runwayml.com/api/
- https://docs.dev.runwayml.com/assets/inputs/

### Google Veo

Google's Vertex AI documentation for Veo 3 documents vertical 9:16 output, 720/1080 resolutions and short clip lengths. Later provider integrations expose additional keyframe/reference capabilities depending on model/version.

Source:
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-0-generate-001

### Seedance / Kling / other engines

Public short-drama systems frequently integrate Seedance, Kling, Veo, MiniMax/Hailuo and others. Xerama should treat them as interchangeable adapters and benchmark them per shot category rather than declare one universal winner.

References:
- https://github.com/ChrisChen667788/wind-comic
- https://github.com/wushaojun321/ai-short-film
- https://github.com/LinHao-city/StoryMind

### Video provider contract

Wind Comic's source suggests a useful capability model. Xerama video adapters should eventually declare:

```text
text_to_video
image_to_video
first_frame
last_frame
subject_reference
native_audio
max_duration
supported_aspects
supported_resolutions
```

## Provider health and fallback

A provider registry is insufficient without health state. Authentication errors, exhausted quota, saturation and repeated transient failures should temporarily remove a provider/model from automatic routing.

```text
request
 -> capability filter
 -> health filter
 -> cost/quality ranking
 -> provider A
    fail -> provider B
    fail -> provider C
```

Record why fallback occurred.

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

Wind Comic further supports temporal micro-beats inside a shot. Xerama's shot contract should optionally describe action progression within the generated clip.

## First-frame / storyboard-first strategy

Strong public implementations create still frames before video generation. This gives the production system a stable target for:

- identity;
- pose;
- framing;
- wardrobe;
- location;
- lighting;
- composition.

Relevant references:
- https://github.com/0xadvait/ai-video-pipeline
- https://github.com/iLearn-Lab/DramaDirector
- https://github.com/ChrisChen667788/wind-comic

Wind Comic also demonstrates rough storyboard/sketch composition references. This suggests separating geometry/blocking approval from expensive final rendering.

## Previous-frame continuity

For adjacent continuous shots, extract the actual final frame from Shot N and use it as a continuity reference for Shot N+1.

This produces a deliberate scheduler tradeoff:

```text
independent shots = parallel for speed
continuous shots  = sequential for continuity
```

Xerama should allow the Director to mark continuity groups.

## Dialogue

Dialogue is a special production problem. Tight singles and over-the-shoulder shots reduce multi-character identity confusion and simplify lip sync/editing.

For dialogue scenes Xerama should prefer coverage such as:

```text
speaker single
reaction single
speaker single
reaction
insert/cutaway
```

instead of forcing a video model to maintain two talking faces for long continuous takes. Add a dialogue-coverage audit before generation.

## Vertical composition

9:16 is not just an output dimension. The prompt compiler should add mobile composition guidance:

- readable subject scale;
- deliberate center/depth staging;
- controlled headroom;
- avoid unnecessary horizontal spread;
- keep subtitle/UI safe areas clear.

## Voice

Voice should be stored as a character asset independent from the video provider.

Each character needs:

- voice provider;
- voice ID;
- language;
- speaking style;
- allowed usage/rights metadata;
- pronunciation dictionary.

This allows the same character to survive provider changes.

## Native audio vs TTS / lip sync

Keep multiple audio strategies behind adapters:

```text
native
  video provider generates scene sound/speech

tts_lipsync
  exact controlled voice + lip sync

hybrid
  native ambience/effects + controlled dialogue
```

Native speech may be natural but can lose exact scripted wording or persistent character voice. Recurring drama dialogue therefore needs benchmark testing rather than a blanket preference.

## Lip sync / performance transfer

Keep lip sync behind an adapter. Public AI drama systems already route among multiple providers, and Runway also documents Act-Two workflows for character performance/dialogue.

Sources:
- https://help.runwayml.com/hc/en-us/articles/41748090660499-Creating-Multi-Character-Dialogues-with-Act-Two
- https://github.com/ChrisChen667788/wind-comic

## Editing

The final assembly should be deterministic code, not generative AI.

Recommended V1:

- FFmpeg/ffprobe;
- timeline JSON/EDL;
- subtitle generation/burn-in;
- audio mixing;
- loudness normalization;
- transitions only when specified;
- final 9:16 render.

Why: once assets are approved, deterministic editing is cheaper, repeatable, testable and does not introduce visual drift.

## Persistent jobs

Every expensive generation should be a persisted job with state, progress and attempt history.

```text
queued
running
retrying
succeeded
failed
cancelled
```

This makes retries, restart recovery, cost attribution and UI progress reliable.

## Persistent assets

Never trust temporary provider URLs as the archive. Download outputs immediately into Xerama-controlled storage and record content hash plus lineage.

Trial 01:

- local filesystem/content-addressed storage;
- SQLite metadata.

Later:

- S3-compatible object storage;
- PostgreSQL.

Both should remain behind adapters/repositories.

## QC

Retain programmatic checks:

- missing file;
- wrong duration;
- wrong aspect ratio;
- black/corrupt frames;
- audio clipping;
- subtitle overflow;
- duplicate shot;
- continuity metadata mismatch.

Add multimodal gates for:

- character resemblance;
- Style Bible similarity;
- continuity;
- lighting/composition;
- shot validity.

Each gate returns `pass`, `warn`, or `block` with a repair recommendation.

## Retention QC

Microdrama also needs story-level production metrics:

- first-three-second hook;
- conflict curve;
- reversal density;
- climax placement;
- cliffhanger;
- dialogue coverage;
- runtime budget.

These checks happen before expensive media generation wherever possible.

## Targeted retakes

Store takes/versions rather than overwriting outputs. If only one shot fails, regenerate only that shot. Segment-level retakes can come later when the cost savings justify the complexity.

## Cost control architecture

Every provider call should record:

```text
provider
model
operation/stage
project/episode/shot
input assets
prompt hash/version
output asset
latency
credits/cost
retry/take number
accepted/rejected
rejection reason
QC scores
```

The primary comparison metric is **cost per accepted asset / accepted video second / accepted episode**, not sticker price per API call.

## Wind Comic source-level reference

See `research/WIND_COMIC_DEEP_DIVE.md` for the detailed architecture extraction and the specific patterns selected for Xerama.