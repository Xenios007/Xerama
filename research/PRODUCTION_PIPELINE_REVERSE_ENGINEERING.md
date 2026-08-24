# AI Microdrama Production Pipeline — Reverse Engineering

_Last researched: 2026-08-24_

## Objective

This document reconstructs the common production pipeline used by current AI short-drama creators/studios from public workflow descriptions. It is intentionally practical and will become the blueprint for Xerama's first implementation.

## Pipeline 1 — Preproduction

### A. Lock delivery format

Common production targets:

- native 9:16 vertical
- approximately 45–120 seconds per episode, with some workflows extending toward 1–3 minutes
- serialized season, often dozens of episodes
- cliffhanger/continuation pressure at episode boundaries
- subtitles designed for phone viewing

Do not let aspect ratio, visual style, or core cast drift casually after production begins.

### B. Story architecture

Public studio workflows consistently build story before expensive visual generation. Typical artifacts:

```text
Concept
→ Season emotional spine
→ Central injustice/desire
→ Secrets and reveals
→ Episode beat sheets
→ Dialogue scripts
```

Ogun describes a hook/stakes/turn/cliffhanger grammar and designing the season's emotional spine/reveal schedule before generation.

### C. Character lock

The most repeated professional practice is to create a reusable character pack before video.

Typical pack:

- root identity portrait
- front/3-quarter/side views
- full-body views
- expressions
- recurring wardrobe
- distinctive details/accessories
- optional short motion/talking reference
- written identity constraint card

When wardrobe/injury/state changes, derive a new state sheet from the same identity root rather than recasting the character.

### D. World lock

Create reusable references for:

- recurring rooms/locations
- time-of-day looks
- props
- vehicles
- wardrobe
- color/grade/style

Limited-location stories are easier and cheaper during early testing.

## Pipeline 2 — Episode decomposition

Do not send a 90-second script to a video model and hope for a finished episode.

Break it into scenes and shots. Public workflows commonly use real coverage concepts:

- establishing/wide
- medium
- close single
- over-the-shoulder
- insert/detail
- reaction

Dialogue is frequently split into singles/reactions because long two-person generative dialogue shots remain harder to control.

A useful internal rule for V1 is one primary action per shot. Public creator guidance often centers around short 4–10 second generations, although newer models can support longer clips.

## Pipeline 3 — Storyboard/reference frames

Before video, produce still keyframes for shots. Benefits:

- approve composition cheaply
- lock character identity
- lock location
- lock wardrobe
- test camera framing
- give image-to-video models a stronger anchor

This is one of the clearest cost-control gates: reject bad identity/composition at still-image cost rather than video cost.

## Pipeline 4 — Video generation

### Image-to-video first where identity matters

Multiple current production guides recommend anchoring video generation on approved reference frames instead of asking text-to-video to reinvent recurring characters each time.

### Route by shot

Current studio/tool guidance increasingly treats model choice as routing rather than loyalty to one model. Different models can be used for:

- dialogue
- action/motion
- hero/cinematic shots
- establishing shots
- B-roll
- cheap filler shots

Xerama therefore needs a `VideoProvider` abstraction plus a future routing policy.

### Expect regeneration

Ogun reports budgeting roughly 20–40% regeneration on first passes; another production article gives roughly 25–40%. Treat this as an operational assumption to test, not a fixed law.

Regenerate at shot level. Never regenerate a full episode merely because one hand/face/prop shot failed.

## Pipeline 5 — Dialogue/audio

Two practical paths exist:

### Native audiovisual generation

If the video model produces usable dialogue/audio, generate it together.

### Separate voice + lip sync

If not:

```text
Script line
→ Character voice/TTS
→ Video shot
→ Lip-sync pass
→ Audio QC
```

Voice identity should be locked just like visual identity.

## Pipeline 6 — Edit

Assemble approved clips in timeline order.

Post stack:

- dialogue leveling
- foley/SFX
- music bed
- transitions where appropriate
- consistent grade/look
- subtitles/captions
- title/end cards
- 9:16 master

Phone-speaker and phone-screen review matters because that is the target viewing environment.

## Pipeline 7 — QC

QC must exist at several gates:

### Asset QC
- same face?
- correct hair/body proportions?
- correct wardrobe?
- correct prop/location?

### Shot QC
- correct action?
- correct character?
- anatomy acceptable?
- lips/audio acceptable?
- camera/composition acceptable?
- no accidental text/artifacts?

### Episode QC
- story continuity?
- pacing?
- subtitle timing?
- audio consistency?
- cliffhanger preserved?

### Series QC
- character drift?
- wardrobe/timeline errors?
- repeated shot patterns?
- secret/reveal contradictions?

## Pipeline 8 — Localization

AI-native production makes localization cheap enough to plan as a system capability:

```text
Master script
→ translation/adaptation
→ localized voice
→ lip sync or regenerated dialogue shot
→ localized subtitles
→ localized master
```

## Xerama V1 simplification

For our trial run, build toward this minimum loop:

```text
Idea
→ 2 story candidates
→ Judge
→ 1 approved mini-story
→ 3 characters max
→ 1–3 locations
→ 3 short episodes
→ Beat sheets
→ Scripts
→ Shot lists
→ Character refs
→ Storyboard frames
→ Video shots
→ Voice/audio
→ Edit
→ QC
```

Do not start by attempting 60 episodes. Prove the production loop with 3 episodes, then scale.

## Sources

- https://ogunstudios.com/blog/how-to-make-ai-short-drama
- https://ogunstudios.com/blog/how-ai-micro-dramas-are-produced
- https://ogunstudios.com/blog/ai-character-consistency-micro-drama
- https://seedancereview.com/blog/seedance-ai-short-drama-workflow/
- https://www.minionarts.com/blogs/how-ai-microdramas-are-made-node-based-pipeline
- https://www.aivid.video/blog/ai-microdrama-how-to-build-a-vertical-series-with-ai
- https://majoflow.com/en/resources/ai-video-animation-workflow/
- https://invideo.io/blog/ai-micro-drama-script-to-episode/
